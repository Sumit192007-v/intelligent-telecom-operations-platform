from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class ComplaintCreateSchema(BaseModel):
    complaint_type: str = Field(..., description="Category of the complaint")
    subject: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    priority: Literal["Low", "Medium", "High", "Critical"] = "Medium"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ComplaintAssignmentSchema(BaseModel):
    assigned_to: int = Field(..., description="User ID of the staff member")
    department: str = Field(..., description="Department name")


class StatusTransitionSchema(BaseModel):
    status: Literal["Pending", "Assigned", "In Progress", "Resolved", "Closed"] = Field(
        ..., description="Desired target status in the lifecycle"
    )
    resolution_notes: Optional[str] = Field(
        default=None,
        description="Optional or required notes detailing resolution or state change",
    )


class ComplaintDetailResponse(BaseModel):
    id: int
    customer_id: int
    complaint_type: str
    subject: str
    description: str
    department: Optional[str] = None
    priority: str
    status: str
    assigned_to: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AllowedTransitionsResponse(BaseModel):
    complaint_id: int
    current_status: str
    allowed_transitions: list[str]
    can_update: bool
