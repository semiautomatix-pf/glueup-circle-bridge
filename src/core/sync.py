from typing import Dict, List, Set, Tuple
from ..clients.glueup import GlueUpClient
from ..clients.circle import CircleClient
from .state import StateCache
import logging

log = logging.getLogger("bridge")

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
    all_spaces: List[Dict],
    dry_run: bool = True
) -> Dict:
    """
    Reconcile a member's space memberships using live data from Circle.

    Checks each space to determine current membership, then computes the diff
    between current and target spaces. Adds/removes member as needed.

    Args:
        circle: Circle API client
        email: Member's email address (used for add/remove operations)
        target_space_ids: List of space IDs the member should belong to
        all_spaces: Pre-fetched list of all spaces (to avoid repeated fetches)
        dry_run: If True, only report what would be done without making changes

    Returns:
        Dict with 'adds', 'removes', and 'details' keys
    """
    result = {"adds": 0, "removes": 0, "details": []}
    target_set: Set[str] = set(target_space_ids)
    current_space_ids: Set[str] = set()

    # Check each space to see if the member is currently in it
    for space in all_spaces:
        space_id = space.get("id")
        if not space_id:
            continue

        try:
            # Fetch all members of this space using pagination
            page = 1
            per_page = 100
            while True:
                members_page = circle.list_space_members(space_id, page=page, per_page=per_page)
                for member in members_page:
                    member_email = normalise_email(member.get("email", ""))
                    if member_email == normalise_email(email):
                        current_space_ids.add(space_id)
                        break
                else:
                    # No match found on this page, check if there are more pages
                    if len(members_page) < per_page:
                        break
                    page += 1
                    continue
                # Member found, break out of pagination loop
                break
        except Exception as e:
            log.warning("Failed to list members for space %s: %s", space_id, e)

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

    # Fetch all spaces once at the start for live reconciliation
    all_spaces = circle.get_all_spaces()

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
                    reconcile_result = reconcile_spaces(circle, email, desired_spaces, all_spaces, dry_run=True)
                    report["space_adds"] += reconcile_result["adds"]
                    report["space_removes"] += reconcile_result["removes"]
                    report["details"].extend(reconcile_result["details"])
                else:
                    circle.invite_member(email=email, name=name, spaces=desired_spaces)
                    report["invited"] += 1
                    report["details"].append({"action": "invite_member", "email": email, "result": "sent"})

                    # Immediately add to cache and save
                    state.set_member_id(email, "pending")
                    state.save()

                    # Reconcile spaces for newly invited member
                    reconcile_result = reconcile_spaces(circle, email, desired_spaces, all_spaces, dry_run=False)
                    report["space_adds"] += reconcile_result["adds"]
                    report["space_removes"] += reconcile_result["removes"]
                    report["details"].extend(reconcile_result["details"])
            except Exception as e:
                log.exception("Failed to invite %s: %s", email, e)
                report["errors"] += 1
            continue

        # Member exists — use live reconciliation instead of cache-based diffing
        reconcile_result = reconcile_spaces(circle, email, desired_spaces, all_spaces, dry_run=dry_run)
        report["space_adds"] += reconcile_result["adds"]
        report["space_removes"] += reconcile_result["removes"]
        report["details"].extend(reconcile_result["details"])

        if reconcile_result["adds"] == 0 and reconcile_result["removes"] == 0:
            report["skipped"] += 1

    state.save()
    return report
