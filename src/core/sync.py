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


def sync_members(glue: GlueUpClient, circle: CircleClient, mapping: Dict, state: StateCache, dry_run: bool = True) -> Dict:
    report = {"created": 0, "invited": 0, "updated": 0, "space_adds": 0, "space_removes": 0, "skipped": 0, "errors": 0, "details": []}

    # Fetch all spaces once at the start
    all_spaces = circle.get_all_spaces()

    # Build membership index upfront for O(1) lookups during reconciliation
    # This avoids O(N*M) API calls (for each user checking all spaces)
    log.info("Building space membership index for %d spaces...", len(all_spaces))
    membership_index = build_space_membership_index(circle, all_spaces)
    log.info("Membership index built with %d unique members", len(membership_index))

    # Pull Glue Up users using paginated method
    users = glue.get_all_users()

    # Fetch memberships per user (you might batch this in production)
    for u in users:
        email = normalise_email(u.get("email") or u.get("email_address") or "")
        name = u.get("name") or f"{u.get('first_name','').strip()} {u.get('last_name','').strip()}".strip()
        if not email:
            report["skipped"] += 1
            continue
        memberships = glue.list_memberships(user_id=u.get("id"))
        # pick the "primary" membership (first active)
        primary = next((m for m in memberships if derive_status(m) == "active"), (memberships[0] if memberships else {}))
        plan_slug = (primary.get("plan_slug") or primary.get("plan_name") or "unmapped").strip().lower()
        desired_spaces = decide_spaces(plan_slug, mapping)

        # resolve Circle member by cache first then maybe lookup (not implemented: full listing for scale)
        member_id = state.lookup_member_id(email)
        if not member_id:
            # try optimistic invite (Circle handles duplicates)
            try:
                if dry_run:
                    report["invited"] += 1
                    report["details"].append({"action": "invite_member", "email": email, "name": name, "spaces": desired_spaces, "dry_run": True})
                    # Also report what space reconciliation would do for the new member
                    reconcile_result = reconcile_spaces(circle, email, desired_spaces, membership_index, dry_run=True)
                    report["space_adds"] += reconcile_result["adds"]
                    report["space_removes"] += reconcile_result["removes"]
                    report["details"].extend(reconcile_result["details"])
                else:
                    circle.invite_member(email=email, name=name, spaces=desired_spaces)
                    report["invited"] += 1
                    report["details"].append({"action": "invite_member", "email": email, "result": "sent"})

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

    return report
