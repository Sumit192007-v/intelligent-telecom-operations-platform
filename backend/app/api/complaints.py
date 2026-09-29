from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_role
from app.models.models import Complaint, User


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
        status="Pending"
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return {
        "message": "Complaint submitted successfully",
        "complaint_id": complaint.id,
        "status": complaint.status
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
            "created_at": complaint.created_at,
            "updated_at": complaint.updated_at,
        }
        for complaint in complaints
    ]
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


@router.put("/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    data: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("staff")),
):
    allowed_statuses = [
        "Pending",
        "Assigned",
        "In Progress",
        "Resolved",
        "Closed",
    ]

    if data.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid complaint status",
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

    complaint.status = data.status

    db.commit()
    db.refresh(complaint)

    return {
        "message": "Complaint status updated successfully",
        "complaint_id": complaint.id,
        "status": complaint.status,
    }