from typing import Any, Dict, List, Set
from ..clients.glueup import GlueUpClient
from ..clients.circle import CircleClient
from .state import StateCache
import logging

log = logging.getLogger("bridge")


def build_space_membership_index(circle: CircleClient, all_spaces: List[Dict]) -> Dict[str, Set[str]]:
    """
    Build a mapping of email -> set of space_ids for all members across all spaces.

    This is a performance optimization that fetches all space memberships once at the
    start of sync, avoiding O(N*M) API calls during reconciliation.

    Args:
        circle: Circle API client
        all_spaces: List of all spaces to index

    Returns:
        Dict mapping normalized email to set of space IDs they belong to
    """
    email_to_spaces: Dict[str, Set[str]] = {}

    for space in all_spaces:
        space_id = space.get("id")
        if not space_id:
            continue

        try:
            # Fetch all members of this space using proper pagination
            page = 1
            per_page = 100
            while True:
                response = circle.list_space_members(space_id, page=page, per_page=per_page)
                members_page = response.get("records") or response.get("members") or response.get("data") or []

                for member in members_page:
                    member_email = normalise_email(member.get("email", ""))
                    if member_email:
                        if member_email not in email_to_spaces:
                            email_to_spaces[member_email] = set()
                        email_to_spaces[member_email].add(space_id)

                # Check has_next_page for pagination (consistent with get_all_spaces)
                if not response.get("has_next_page", False):
                    break
                page += 1

        except Exception as e:
            log.warning("Failed to list members for space %s: %s", space_id, e)

    return email_to_spaces


def safe_save_state(state: StateCache) -> bool:
    """
    Safely save state cache with error handling.

    Returns:
        True if save succeeded, False otherwise
    """
    try:
        state.save()
        return True
    except Exception as e:
        log.error("Failed to save state cache: %s", e)
        return False

def normalise_email(email: str) -> str:
    return (email or "").strip().lower()

def decide_spaces(plan_slug: str, mapping: Dict) -> List[str]:
    default_spaces = mapping.get("default_spaces", []) or []
    plan_spaces = mapping.get("plans_to_spaces", {}).get(plan_slug, [])
    return list(dict.fromkeys(default_spaces + plan_spaces))  # de-dup, maintain order

def derive_status(membership: Dict) -> str:
    # very light; adapt to your Glue Up schema
    status = (membership.get("status") or "").lower()
    if status in ("active", "current"):
        return "active"
    if status in ("expired", "lapsed"):
        return "lapsed"
    return status or "unknown"


def normalize_individual_member(record: Dict) -> Dict[str, Any]:
    """Normalize an individual member record from GlueUp to standard format.

    Args:
        record: Individual member record with 'membership' and 'individualMember' keys

    Returns:
        Normalized member dict with email, name, plan_slug, member_type, corporate_name
    """
    membership = record.get("membership", {})
    individual = record.get("individualMember", {})

    # Extract email from nested structure
    email_obj = individual.get("emailAddress", {})
    email = email_obj.get("value", "") if isinstance(email_obj, dict) else str(email_obj)

    # Extract name
    given_name = individual.get("givenName", "")
    family_name = individual.get("familyName", "")
    name = f"{given_name} {family_name}".strip()

    # Get membership type title as plan slug
    membership_type = membership.get("membershipType", {})
    plan_slug = (
        membership_type.get("title") or membership_type.get("internalTitle") or "unmapped"
    ).strip().lower()

    return {
        "email": normalise_email(email),
        "name": name,
        "plan_slug": plan_slug,
        "member_type": "individual",
        "corporate_name": None,
    }


def normalize_corporate_contacts(corp_record: Dict) -> List[Dict[str, Any]]:
    """Normalize a corporate membership record to list of contact members.

    Yields both admin contact and all member contacts.

    Args:
        corp_record: Corporate membership record with 'membership', 'adminContact', 'memberContacts'

    Returns:
        List of normalized member dicts (admin + member contacts)
    """
    membership = corp_record.get("membership", {})
    admin_contact = corp_record.get("adminContact", {})
    member_contacts = corp_record.get("memberContacts", []) or []

    # Get membership type for plan slug
    membership_type = membership.get("membershipType", {})
    plan_slug = (
        membership_type.get("title") or membership_type.get("internalTitle") or "unmapped"
    ).strip().lower()

    # Get corporate name
    corporate_name = membership.get("name", "Unknown Corporation")

    contacts = []

    # Process admin contact
    if admin_contact:
        admin_email_obj = admin_contact.get("emailAddress", {})
        admin_email = (
            admin_email_obj.get("value", "")
            if isinstance(admin_email_obj, dict)
            else str(admin_email_obj)
        )
        admin_given = admin_contact.get("givenName", "")
        admin_family = admin_contact.get("familyName", "")
        admin_name = f"{admin_given} {admin_family}".strip()

        if admin_email:
            contacts.append({
                "email": normalise_email(admin_email),
                "name": admin_name,
                "plan_slug": plan_slug,
                "member_type": "corporate_admin",
                "corporate_name": corporate_name,
            })

    # Process member contacts
    for contact in member_contacts:
        contact_email_obj = contact.get("emailAddress", {})
        contact_email = (
            contact_email_obj.get("value", "")
            if isinstance(contact_email_obj, dict)
            else str(contact_email_obj)
        )
        contact_given = contact.get("givenName", "")
        contact_family = contact.get("familyName", "")
        contact_name = f"{contact_given} {contact_family}".strip()

        if contact_email:
            contacts.append({
                "email": normalise_email(contact_email),
                "name": contact_name,
                "plan_slug": plan_slug,
                "member_type": "corporate_contact",
                "corporate_name": corporate_name,
            })

    return contacts


def get_all_normalized_members(glue: GlueUpClient, organization_id: str) -> List[Dict[str, Any]]:
    """Fetch and normalize all members (individual + corporate contacts).

    Args:
        glue: GlueUp API client
        organization_id: Organization ID for API requests

    Returns:
        List of normalized member dicts with unified structure
    """
    all_members = []

    # Fetch both types
    unified = glue.get_all_members_unified(organization_id)

    # Normalize individual members
    for record in unified["individual"]:
        try:
            normalized = normalize_individual_member(record)
            if normalized["email"]:  # Only include if email exists
                all_members.append(normalized)
        except Exception as e:
            log.warning("Failed to normalize individual member: %s", e)

    # Normalize corporate contacts
    for corp_record in unified["corporate"]:
        try:
            contacts = normalize_corporate_contacts(corp_record)
            all_members.extend(contacts)
        except Exception as e:
            log.warning("Failed to normalize corporate membership: %s", e)

    log.info(
        "Normalized %d total members (%d individual, %d corporate)",
        len(all_members),
        len(unified["individual"]),
        sum(len(normalize_corporate_contacts(c)) for c in unified["corporate"]),
    )

    return all_members


def reconcile_spaces(
    circle: CircleClient,
    email: str,
    target_space_ids: List[str],
    membership_index: Dict[str, Set[str]],
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    Reconcile a member's space memberships using a pre-built membership index.

    Uses the membership index to determine current membership (O(1) lookup),
    then computes the diff between current and target spaces.
    Adds/removes member as needed.

    Args:
        circle: Circle API client
        email: Member's email address (used for add/remove operations)
        target_space_ids: List of space IDs the member should belong to
        membership_index: Pre-built mapping of email -> set of space IDs
        dry_run: If True, only report what would be done without making changes

    Returns:
        Dict with 'adds', 'removes', and 'details' keys
    """
    result: Dict[str, Any] = {"adds": 0, "removes": 0, "details": []}
    target_set: Set[str] = set(target_space_ids)

    # O(1) lookup using the pre-built membership index
    normalized_email = normalise_email(email)
    current_space_ids: Set[str] = membership_index.get(normalized_email, set()).copy()

    # Compute the diff
    to_add = sorted(target_set - current_space_ids)
    to_remove = sorted(current_space_ids - target_set)

    # Add member to spaces they should be in
    for space_id in to_add:
        if dry_run:
            result["adds"] += 1
            result["details"].append({
                "action": "add_to_space",
                "email": email,
                "space_id": space_id,
                "dry_run": True
            })
        else:
            try:
                circle.add_member_to_space(email, space_id)
                result["adds"] += 1
                result["details"].append({
                    "action": "add_to_space",
                    "email": email,
                    "space_id": space_id,
                    "result": "success"
                })
            except Exception as e:
                log.exception("Failed to add %s to space %s: %s", email, space_id, e)
                result["details"].append({
                    "action": "add_to_space",
                    "email": email,
                    "space_id": space_id,
                    "result": "error",
                    "error": str(e)
                })

    # Remove member from spaces they should not be in
    for space_id in to_remove:
        if dry_run:
            result["removes"] += 1
            result["details"].append({
                "action": "remove_from_space",
                "email": email,
                "space_id": space_id,
                "dry_run": True
            })
        else:
            try:
                circle.remove_member_from_space(email, space_id)
                result["removes"] += 1
                result["details"].append({
                    "action": "remove_from_space",
                    "email": email,
                    "space_id": space_id,
                    "result": "success"
                })
            except Exception as e:
                log.exception("Failed to remove %s from space %s: %s", email, space_id, e)
                result["details"].append({
                    "action": "remove_from_space",
                    "email": email,
                    "space_id": space_id,
                    "result": "error",
                    "error": str(e)
                })

    return result


def validate_cache_against_circle(circle: CircleClient, state: StateCache, repair: bool = False) -> Dict:
    """Validate state cache against Circle API and optionally repair discrepancies.

    Args:
        circle: Circle API client
        state: State cache to validate
        repair: If True, fix discrepancies by updating cache

    Returns:
        Dict with validation report: valid, invalid, missing, repaired counts
    """
    report = {
        "valid": 0,
        "invalid": 0,
        "missing_in_circle": 0,
        "missing_in_cache": 0,
        "repaired": 0,
        "details": [],
    }

    log.info("Validating cache against Circle API (repair=%s)...", repair)

    # Fetch all Circle members
    try:
        all_circle_members = circle.get_all_members()
        circle_emails = {normalise_email(m.get("email", "")): m.get("id") for m in all_circle_members if m.get("email")}
        log.info("Fetched %d members from Circle", len(circle_emails))
    except Exception as e:
        log.error("Failed to fetch Circle members: %s", e)
        return {"error": str(e)}

    # Check cache entries against Circle
    cache_data = state._data.get("email_to_member_id", {})
    for email, cached_id in cache_data.items():
        normalized = normalise_email(email)
        if normalized in circle_emails:
            report["valid"] += 1
        else:
            report["missing_in_circle"] += 1
            report["details"].append({
                "issue": "missing_in_circle",
                "email": email,
                "cached_id": cached_id,
            })

    # Check Circle members not in cache
    for email, circle_id in circle_emails.items():
        if email not in cache_data:
            report["missing_in_cache"] += 1
            report["details"].append({
                "issue": "missing_in_cache",
                "email": email,
                "circle_id": circle_id,
            })
            if repair:
                state.set_member_id(email, circle_id)
                report["repaired"] += 1

    # Save repaired cache
    if repair and report["repaired"] > 0:
        if safe_save_state(state):
            log.info("Cache repaired: %d entries added", report["repaired"])
        else:
            log.error("Failed to save repaired cache")

    log.info("Validation complete: %d valid, %d invalid, %d missing in Circle, %d missing in cache, %d repaired",
             report["valid"], report["invalid"], report["missing_in_circle"], report["missing_in_cache"], report["repaired"])

    return report


def sync_members(glue: GlueUpClient, circle: CircleClient, mapping: Dict, state: StateCache, organization_id: str, dry_run: bool = True) -> Dict:
    report = {
        "created": 0,
        "invited": 0,
        "updated": 0,
        "space_adds": 0,
        "space_removes": 0,
        "skipped": 0,
        "errors": 0,
        "duplicates_skipped": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "member_types": {
            "individual": 0,
            "corporate_admin": 0,
            "corporate_contact": 0,
        },
        "details": [],
    }

    # Fetch all spaces once at the start
    all_spaces = circle.get_all_spaces()

    # Build membership index upfront for O(1) lookups during reconciliation
    # This avoids O(N*M) API calls (for each user checking all spaces)
    log.info("Building space membership index for %d spaces...", len(all_spaces))
    membership_index = build_space_membership_index(circle, all_spaces)
    log.info("Membership index built with %d unique members", len(membership_index))

    # Fetch and normalize all members (individual + corporate contacts)
    log.info("Fetching and normalizing members from Glue Up...")
    members = get_all_normalized_members(glue, organization_id)
    log.info("Fetched %d normalized members from Glue Up", len(members))

    # In-batch deduplication: track emails we've seen in this sync
    seen_in_batch = set()

    # Process each normalized member
    for member in members:
        email = member["email"]
        name = member["name"]
        plan_slug = member["plan_slug"]
        member_type = member["member_type"]
        corporate_name = member.get("corporate_name")

        # Track member types
        if member_type in report["member_types"]:
            report["member_types"][member_type] += 1

        # In-batch deduplication
        if email in seen_in_batch:
            report["duplicates_skipped"] += 1
            log.debug("Skipping duplicate email in batch: %s", email)
            continue
        seen_in_batch.add(email)

        if not email:
            report["skipped"] += 1
            continue

        desired_spaces = decide_spaces(plan_slug, mapping)

        # Resolve Circle member by cache first
        member_id = state.lookup_member_id(email)

        # Cache hit tracking
        if member_id:
            report["cache_hits"] += 1
        else:
            report["cache_misses"] += 1

            # Cross-check with membership_index (cache may be stale)
            if normalise_email(email) in membership_index:
                log.info("Found %s in Circle but not in cache - updating cache", email)
                state.set_member_id(email, "known")
                member_id = "known"
                report["cache_hits"] += 1
                report["cache_misses"] -= 1

        if not member_id:
            # Try optimistic invite (Circle handles duplicates)
            try:
                if dry_run:
                    report["invited"] += 1
                    detail = {
                        "action": "invite_member",
                        "email": email,
                        "name": name,
                        "membership_type": plan_slug,
                        "member_type": member_type,
                        "spaces": desired_spaces,
                        "dry_run": True,
                    }
                    if corporate_name:
                        detail["corporate_name"] = corporate_name
                    report["details"].append(detail)

                    # Also report what space reconciliation would do for the new member
                    reconcile_result = reconcile_spaces(circle, email, desired_spaces, membership_index, dry_run=True)
                    report["space_adds"] += reconcile_result["adds"]
                    report["space_removes"] += reconcile_result["removes"]
                    report["details"].extend(reconcile_result["details"])
                else:
                    circle.invite_member(email=email, name=name, spaces=desired_spaces)
                    report["invited"] += 1
                    detail = {"action": "invite_member", "email": email, "result": "sent", "member_type": member_type}
                    if corporate_name:
                        detail["corporate_name"] = corporate_name
                    report["details"].append(detail)

                    # Immediately add to cache with error recovery
                    state.set_member_id(email, "pending")
                    if not safe_save_state(state):
                        log.warning("State save failed after inviting %s; continuing sync", email)

                    # Reconcile spaces for newly invited member
                    reconcile_result = reconcile_spaces(circle, email, desired_spaces, membership_index, dry_run=False)
                    report["space_adds"] += reconcile_result["adds"]
                    report["space_removes"] += reconcile_result["removes"]
                    report["details"].extend(reconcile_result["details"])
            except Exception as e:
                log.exception("Failed to invite %s: %s", email, e)
                report["errors"] += 1
            continue

        # Member exists — use live reconciliation with pre-built index
        reconcile_result = reconcile_spaces(circle, email, desired_spaces, membership_index, dry_run=dry_run)
        report["space_adds"] += reconcile_result["adds"]
        report["space_removes"] += reconcile_result["removes"]
        report["details"].extend(reconcile_result["details"])

        if reconcile_result["adds"] == 0 and reconcile_result["removes"] == 0:
            report["skipped"] += 1

    # Final state save with error recovery
    if not safe_save_state(state):
        log.error("Final state save failed; some changes may not be persisted")

    # Log member type summary
    log.info("Member types processed: %s", report["member_types"])

    return report
