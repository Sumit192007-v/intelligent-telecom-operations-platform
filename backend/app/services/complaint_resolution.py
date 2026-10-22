"""Complaint Resolution and Lifecycle Tracking Service

Validates state transitions, enforces role-based authorization for status updates,
and manages resolution timestamps and audit notes.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Complaint, User

LIFECYCLE_STAGES = ("Pending", "Assigned", "In Progress", "Resolved", "Closed")

# Allowed transitions matrix for staff operations:
# Key: current status -> Value: set of permissible next statuses
ALLOWED_TRANSITIONS = {
    "Pending": {"Pending", "Assigned", "In Progress", "Closed"},
    "Assigned": {"Assigned", "In Progress", "Pending", "Closed"},
    "In Progress": {"In Progress", "Resolved", "Assigned"},
    "Resolved": {"Resolved", "Closed", "In Progress"},
    "Closed": {"Closed", "In Progress"},
}

# Customer-allowed status transitions:
# Customers can only confirm closing a complaint that staff has marked Resolved
CUSTOMER_ALLOWED_TRANSITIONS = {
    "Resolved": {"Resolved", "Closed"},
}


def get_allowed_transitions_for_role(current_status: str, role: str) -> list[str]:
    """Return the list of statuses the given role can transition the complaint into."""
    from app.auth import EMPLOYEE_ROLES
    if role == "customer":
        allowed = CUSTOMER_ALLOWED_TRANSITIONS.get(current_status, {current_status})
    elif role == "staff" or role in EMPLOYEE_ROLES:
        allowed = ALLOWED_TRANSITIONS.get(current_status, {current_status})
    else:
        allowed = {current_status}

    # Sort according to standard lifecycle order
    order = {s: i for i, s in enumerate(LIFECYCLE_STAGES)}
    return sorted(list(allowed), key=lambda s: order.get(s, 99))


def validate_status_transition(
    complaint: Complaint,
    new_status: str,
    user: User,
) -> None:
    """Validate that the requested transition is permitted for the given user role.
    
    Raises HTTPException(400) if the transition is invalid, or
    HTTPException(403) if the user is not authorized.
    """
    if new_status not in LIFECYCLE_STAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid complaint status: '{new_status}'. Allowed statuses are {list(LIFECYCLE_STAGES)}.",
        )

    current_status = complaint.status or "Pending"

    # Customers may only operate on their own complaints
    if user.role == "customer":
        if complaint.customer_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage your own complaints.",
            )

        permitted = CUSTOMER_ALLOWED_TRANSITIONS.get(current_status, set())
        if new_status not in permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Customers cannot change complaint status from '{current_status}' to '{new_status}'. "
                    "Customers may only close complaints once they have been marked 'Resolved'."
                ),
            )
        return

    # Staff and employee role transitions
    from app.auth import EMPLOYEE_ROLES, MANAGEMENT_ROLES, normalize_department
    if user.role == "staff" or user.role in EMPLOYEE_ROLES:
        # Department scoping:
        if complaint.department is not None and user.role not in MANAGEMENT_ROLES:
            if user.department is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Staff members without an assigned department cannot modify complaints belonging to a named department.",
                )
            user_dept = normalize_department(user.department)
            comp_dept = normalize_department(complaint.department)
            if user_dept != comp_dept:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Staff members in '{user.department}' cannot modify complaints belonging to the '{complaint.department}' department.",
                )

        permitted = ALLOWED_TRANSITIONS.get(current_status, set())
        if new_status not in permitted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Illegal lifecycle transition: cannot move complaint from '{current_status}' "
                    f"to '{new_status}'. Allowed next stages: {sorted(list(permitted))}."
                ),
            )
        return

    # Any other role is unauthorized
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Unauthorized to update complaint status.",
    )


def transition_complaint_status(
    db: Session,
    complaint: Complaint,
    new_status: str,
    user: User,
    resolution_notes: Optional[str] = None,
) -> Complaint:
    """Execute a validated lifecycle status transition on a complaint.
    
    - Validates business transition rules and role authorization.
    - Sets resolved_at timestamp when entering 'Resolved'.
    - Clears resolved_at timestamp when entering 'In Progress' (reopening from Resolved or Closed).
    - Stores resolution notes if provided and supported by model.
    - Persists changes via the active SQLAlchemy session.
    """
    validate_status_transition(complaint, new_status, user)

    previous_status = complaint.status
    complaint.status = new_status

    # Resolution timestamp tracking
    now_utc = datetime.now(timezone.utc)
    if new_status == "Resolved" and previous_status != "Resolved":
        if hasattr(complaint, "resolved_at"):
            complaint.resolved_at = now_utc
    elif new_status == "In Progress":
        # Moving to In Progress (including reopening from Resolved or Closed) clears the resolved timestamp
        if hasattr(complaint, "resolved_at"):
            complaint.resolved_at = None

    # Resolution notes tracking
    if resolution_notes is not None and hasattr(complaint, "resolution_notes"):
        complaint.resolution_notes = resolution_notes.strip()

    db.commit()
    db.refresh(complaint)
    return complaint
