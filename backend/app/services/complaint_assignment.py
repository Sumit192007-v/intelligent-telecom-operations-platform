"""Complaint Assignment Service

Handles automatic and manual complaint assignment, department determination,
and workload-balanced staff allocation based on real database records.
"""

from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Complaint, User

# Configured departments aligning with existing platform definitions
CONFIGURED_DEPARTMENTS = ("Technical", "Network", "Billing", "Customer Support")

# Explicit business mapping from complaint category to department
CATEGORY_TO_DEPARTMENT_MAP = {
    "network issue": "Network",
    "call issue": "Network",
    "internet issue": "Technical",
    "technical issue": "Technical",
    "billing issue": "Billing",
    "customer support issue": "Customer Support",
    "customer service issue": "Customer Support",
}


def resolve_department_for_category(category: Optional[str]) -> Optional[str]:
    """Map a complaint category string to a valid department.
    
    Returns None for ambiguous, unsupported, or 'Other' categories to enable
    an unassigned triage/review workflow.
    """
    if not category:
        return None

    normalized = category.strip().lower()

    # Ambiguous or fallback categories explicitly return None for manual review
    if normalized in ("other", "general", "unknown", "unspecified"):
        return None

    mapped = CATEGORY_TO_DEPARTMENT_MAP.get(normalized)
    if mapped and mapped in CONFIGURED_DEPARTMENTS:
        return mapped

    # Direct match if caller provided exact department name
    for dept in CONFIGURED_DEPARTMENTS:
        if normalized == dept.lower():
            return dept

    return None


def get_eligible_staff_members(db: Session, department: str) -> list[User]:
    """Retrieve all staff members registered in the specified department."""
    return (
        db.query(User)
        .filter(User.role == "staff", User.department == department)
        .order_by(User.id.asc())
        .all()
    )


def find_least_loaded_staff(db: Session, department: str) -> Optional[User]:
    """Find the eligible staff member in the given department with the lowest active workload.
    
    Active workload is defined as complaints currently in 'Assigned' or 'In Progress'.
    Ties are broken deterministically by the lowest user ID.
    """
    eligible_staff = get_eligible_staff_members(db, department)
    if not eligible_staff:
        return None

    staff_ids = [s.id for s in eligible_staff]

    # Query active complaint counts per staff member in this department
    counts_query = (
        db.query(Complaint.assigned_to, func.count(Complaint.id).label("workload"))
        .filter(
            Complaint.assigned_to.in_(staff_ids),
            Complaint.status.in_(["Assigned", "In Progress"]),
        )
        .group_by(Complaint.assigned_to)
        .all()
    )

    workload_map = {staff_id: 0 for staff_id in staff_ids}
    for assigned_to_id, count in counts_query:
        if assigned_to_id in workload_map:
            workload_map[assigned_to_id] = count

    # Select candidate with minimal workload, tie-breaking by lowest staff id
    best_candidate = min(
        eligible_staff,
        key=lambda staff: (workload_map.get(staff.id, 0), staff.id),
    )

    return best_candidate


def auto_assign_complaint(
    db: Session,
    complaint: Complaint,
    force: bool = False,
) -> Complaint:
    """Automatically route and assign a complaint based on its category and staff workload.
    
    - Resolves the target department from business rules.
    - If category is ambiguous or unconfigured, leaves department and assignee as None
      with status 'Pending' for manual triage.
    - If department is resolved but no staff is available, sets department and keeps
      status 'Pending' with assigned_to = None.
    - If eligible staff is available, selects the least-loaded staff member,
      sets assigned_to, and updates status to 'Assigned'.
    - Prevents accidental overwriting of already assigned, in-progress, or closed complaints unless force=True.
    """
    # Guard against accidental reassignment of already assigned or active complaints
    if not force and (
        complaint.status in ("Assigned", "In Progress", "Resolved", "Closed")
        or complaint.assigned_to is not None
    ):
        return complaint

    target_department = resolve_department_for_category(complaint.complaint_type)

    if not target_department:
        # Ambiguous / unsupported category: remains pending for manual triage
        complaint.department = None
        complaint.assigned_to = None
        complaint.status = "Pending"
        return complaint

    complaint.department = target_department
    assignee = find_least_loaded_staff(db, target_department)

    if assignee:
        complaint.assigned_to = assignee.id
        complaint.status = "Assigned"
    else:
        # Department assigned, but no individual staff eligible: remains pending triage
        complaint.assigned_to = None
        complaint.status = "Pending"

    return complaint
