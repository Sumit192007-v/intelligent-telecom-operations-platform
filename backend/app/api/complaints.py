from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_role
from app.models.models import Complaint, User
from app.services.complaint_assignment import auto_assign_complaint
from app.services.complaint_resolution import transition_complaint_status


router = APIRouter(prefix="/complaints", tags=["Complaints"])
DEPARTMENTS = ("Technical", "Network", "Billing", "Customer Support")


class ComplaintCreate(BaseModel):
    complaint_type: str
    subject: str
    description: str
    priority: Literal["Low", "Medium", "High", "Critical"] = "Medium"
    latitude: float | None = None
    longitude: float | None = None


@router.post("/")
def create_complaint(
    data: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("customer")),
):
    complaint = Complaint(
        customer_id=current_user.id,
        complaint_type=data.complaint_type,
        subject=data.subject,
        description=data.description,
        priority=data.priority,
        latitude=data.latitude,
        longitude=data.longitude,
        status="Pending",
    )

    # Automatic assignment and department routing based on business rules
    auto_assign_complaint(db, complaint)

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return {
        "message": "Complaint submitted successfully",
        "complaint_id": complaint.id,
        "status": complaint.status,
        "department": complaint.department,
        "assigned_to": complaint.assigned_to,
    }
@router.get("/")
def get_all_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("staff")),
):
    complaints = (
        db.query(Complaint)
        .order_by(Complaint.created_at.desc())
        .all()
    )

    return [
        {
            "id": complaint.id,
            "customer_id": complaint.customer_id,
            "complaint_type": complaint.complaint_type,
            "subject": complaint.subject,
            "description": complaint.description,
            "department": complaint.department,
            "priority": complaint.priority,
            "status": complaint.status,
            "assigned_to": complaint.assigned_to,
            "resolved_at": complaint.resolved_at,
            "resolution_notes": complaint.resolution_notes,
            "created_at": complaint.created_at,
            "updated_at": complaint.updated_at,
        }
        for complaint in complaints
    ]
@router.get("/staff")
def get_staff(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("staff")),
):
    staff = (
        db.query(User)
        .filter(User.role == "staff")
        .order_by(User.name)
        .all()
    )

    return [
        {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "department": user.department,
        }
        for user in staff
    ]
@router.get("/summary")
def get_complaint_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("staff")),
):
    total = db.query(Complaint).count()

    pending = (
        db.query(Complaint)
        .filter(Complaint.status == "Pending")
        .count()
    )

    assigned = (
        db.query(Complaint)
        .filter(Complaint.status == "Assigned")
        .count()
    )

    in_progress = (
        db.query(Complaint)
        .filter(Complaint.status == "In Progress")
        .count()
    )

    resolved = (
        db.query(Complaint)
        .filter(Complaint.status == "Resolved")
        .count()
    )

    closed = (
        db.query(Complaint)
        .filter(Complaint.status == "Closed")
        .count()
    )

    return {
        "total": total,
        "pending": pending,
        "assigned": assigned,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed,
    }
@router.get("/departments")
def get_department_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("staff")),
):
    result = []

    for department in DEPARTMENTS:
        count = (
            db.query(Complaint)
            .filter(Complaint.department == department)
            .count()
        )

        result.append({
            "department": department,
            "complaints": count,
        })

    return result
@router.get("/my")
def get_customer_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("customer")),
):
    complaints = (
        db.query(Complaint)
        .filter(Complaint.customer_id == current_user.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )

    return [
        {
            "id": complaint.id,
            "complaint_type": complaint.complaint_type,
            "subject": complaint.subject,
            "description": complaint.description,
            "department": complaint.department,
            "priority": complaint.priority,
            "status": complaint.status,
            "assigned_to": complaint.assigned_to,
            "resolved_at": complaint.resolved_at,
            "resolution_notes": complaint.resolution_notes,
            "created_at": complaint.created_at,
            "updated_at": complaint.updated_at,
        }
        for complaint in complaints
    ]


@router.get("/{complaint_id}")
def get_complaint_by_id(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    # Customers can only view their own complaints; staff can view any
    if current_user.role == "customer":
        if complaint.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this complaint",
            )
    elif current_user.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return {
        "id": complaint.id,
        "customer_id": complaint.customer_id,
        "complaint_type": complaint.complaint_type,
        "subject": complaint.subject,
        "description": complaint.description,
        "department": complaint.department,
        "priority": complaint.priority,
        "status": complaint.status,
        "assigned_to": complaint.assigned_to,
        "resolved_at": complaint.resolved_at,
        "resolution_notes": complaint.resolution_notes,
        "created_at": complaint.created_at,
        "updated_at": complaint.updated_at,
    }


class ComplaintAssignment(BaseModel):
    assigned_to: int
    department: str


@router.put("/{complaint_id}/assign")
def assign_complaint(
    complaint_id: int,
    data: ComplaintAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("staff")),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    # Department scoping:
    # 1. Staff must be authorized to manage complaint in its current department
    if complaint.department is not None:
        if current_user.department is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff members without an assigned department cannot reassign complaints belonging to a named department.",
            )
        if current_user.department != complaint.department:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Staff members in '{current_user.department}' cannot reassign complaints belonging to the '{complaint.department}' department.",
            )

    # 2. Staff cannot transfer complaints to a department other than their own
    if current_user.department is not None and data.department != current_user.department:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Staff members in '{current_user.department}' cannot transfer complaints to the '{data.department}' department.",
        )

    assignee = db.query(User).filter(User.id == data.assigned_to).first()
    if assignee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found",
        )
    if assignee.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee must have the staff role",
        )
    if data.department not in DEPARTMENTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid department",
        )
    if assignee.department is not None and assignee.department != data.department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assignee belongs to department '{assignee.department}', cannot assign to '{data.department}'",
        )

    complaint.assigned_to = data.assigned_to
    complaint.department = data.department
    complaint.status = "Assigned"

    db.commit()
    db.refresh(complaint)

    return {
        "message": "Complaint assigned successfully",
        "complaint_id": complaint.id,
        "assigned_to": complaint.assigned_to,
        "department": complaint.department,
        "status": complaint.status,
    }
class ComplaintStatusUpdate(BaseModel):
    status: str
    resolution_notes: str | None = None


@router.put("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    data: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Customer authorization guard: customers may only close their own resolved complaint
    if current_user.role == "customer":
        if data.status != "Closed":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customers cannot update complaint status to this state.",
            )
    elif current_user.role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    # Use resolution service to validate lifecycle transitions, record timestamps, and save notes
    complaint = transition_complaint_status(
        db=db,
        complaint=complaint,
        new_status=data.status,
        user=current_user,
        resolution_notes=data.resolution_notes,
    )

    return {
        "message": "Complaint status updated successfully",
        "complaint_id": complaint.id,
        "status": complaint.status,
        "resolved_at": complaint.resolved_at,
        "resolution_notes": complaint.resolution_notes,
        "updated_at": complaint.updated_at,
    }