"""Tests for Automatic Complaint Assignment and Resolution Tracking Services."""

from datetime import datetime, timezone
import pytest
from fastapi import HTTPException

from app.models.models import Complaint, User
from app.services.complaint_assignment import (
    auto_assign_complaint,
    find_least_loaded_staff,
    resolve_department_for_category,
)
from app.services.complaint_resolution import (
    get_allowed_transitions_for_role,
    transition_complaint_status,
    validate_status_transition,
)


def create_staff_user(sessions, department, name="Staff User"):
    """Helper to create a staff user with a specific department."""
    with sessions() as session:
        user = User(
            name=name,
            email=f"{name.lower().replace(' ', '_')}_{department.lower()}@telecom.test",
            password_hash="mock_hash",
            role="staff",
            department=department,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def create_test_complaint(sessions, customer_id, complaint_type="Network Issue", status="Pending"):
    """Helper to create a test complaint."""
    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type=complaint_type,
            subject=f"Issue with {complaint_type}",
            description="Detailed problem report",
            priority="Medium",
            status=status,
        )
        session.add(complaint)
        session.commit()
        session.refresh(complaint)
        return complaint.id


def test_department_routing_business_rules():
    """Verify category to department mapping rules."""
    assert resolve_department_for_category("Network Issue") == "Network"
    assert resolve_department_for_category("Call Issue") == "Network"
    assert resolve_department_for_category("Internet Issue") == "Technical"
    assert resolve_department_for_category("Technical Issue") == "Technical"
    assert resolve_department_for_category("Billing Issue") == "Billing"
    assert resolve_department_for_category("Customer Support Issue") == "Customer Support"
    # Ambiguous or fallback categories should resolve to None for manual triage
    assert resolve_department_for_category("Other") is None
    assert resolve_department_for_category("General") is None
    assert resolve_department_for_category("Unknown Category") is None
    assert resolve_department_for_category("") is None
    assert resolve_department_for_category(None) is None


def test_auto_assignment_selects_least_loaded_staff(api_client, create_user):
    """Staff member with lowest active workload in the department should be selected."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")

    staff1_id = create_staff_user(sessions, "Network", "Agent Alpha")
    staff2_id = create_staff_user(sessions, "Network", "Agent Beta")

    with sessions() as session:
        # Give staff1 an existing active complaint (Assigned)
        c_active = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Alpha's task",
            description="desc",
            department="Network",
            status="Assigned",
            assigned_to=staff1_id,
        )
        session.add(c_active)

        # Create new unassigned complaint
        new_complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="New network problem",
            description="desc",
            status="Pending",
        )
        session.add(new_complaint)
        session.commit()

        # Run auto-assignment
        assigned = auto_assign_complaint(session, new_complaint)
        session.commit()

        # Staff2 should be picked because staff2 has 0 active complaints vs staff1 has 1
        assert assigned.department == "Network"
        assert assigned.assigned_to == staff2_id
        assert assigned.status == "Assigned"


def test_auto_assignment_deterministic_tie_breaker(api_client, create_user):
    """When eligible staff members have identical workloads, pick the lowest user ID."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")

    staff1_id = create_staff_user(sessions, "Billing", "Bill Agent 1")
    staff2_id = create_staff_user(sessions, "Billing", "Bill Agent 2")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Billing Issue",
            subject="Overcharge",
            description="desc",
            status="Pending",
        )
        session.add(complaint)
        session.commit()

        assigned = auto_assign_complaint(session, complaint)
        session.commit()

        assert assigned.department == "Billing"
        assert assigned.assigned_to == min(staff1_id, staff2_id)
        assert assigned.status == "Assigned"


def test_auto_assignment_handles_ambiguous_category(api_client, create_user):
    """Ambiguous category remains pending without assignment for manual staff review."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    create_staff_user(sessions, "Customer Support", "Support Agent")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Other",
            subject="Weird situation",
            description="Not categorized",
            status="Pending",
        )
        session.add(complaint)
        session.commit()

        assigned = auto_assign_complaint(session, complaint)
        session.commit()

        assert assigned.department is None
        assert assigned.assigned_to is None
        assert assigned.status == "Pending"


def test_auto_assignment_handles_empty_department(api_client, create_user):
    """When a department has no staff, department is set but assigned_to remains None."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Technical Issue",
            subject="Router reset failed",
            description="Technical problem",
            status="Pending",
        )
        session.add(complaint)
        session.commit()

        # No Technical staff created
        assigned = auto_assign_complaint(session, complaint)
        session.commit()

        assert assigned.department == "Technical"
        assert assigned.assigned_to is None
        assert assigned.status == "Pending"


def test_auto_assignment_guards_against_accidental_reassignment(api_client, create_user):
    """Active in-progress or closed complaints are not automatically overwritten."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff_id = create_staff_user(sessions, "Network", "Agent Alpha")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Ongoing fix",
            description="desc",
            department="Network",
            status="In Progress",
            assigned_to=staff_id,
        )
        session.add(complaint)
        session.commit()

        # Attempt auto-assign without force
        result = auto_assign_complaint(session, complaint, force=False)
        assert result.assigned_to == staff_id
        assert result.status == "In Progress"


def test_allowed_lifecycle_transitions():
    """Verify allowed transitions for staff and customer roles."""
    # Staff allowed next stages
    assert "Assigned" in get_allowed_transitions_for_role("Pending", "staff")
    assert "Closed" in get_allowed_transitions_for_role("Pending", "staff")
    assert "Resolved" not in get_allowed_transitions_for_role("Pending", "staff")

    assert "In Progress" in get_allowed_transitions_for_role("Assigned", "staff")
    assert "Resolved" in get_allowed_transitions_for_role("In Progress", "staff")
    assert "Closed" in get_allowed_transitions_for_role("Resolved", "staff")
    assert "In Progress" in get_allowed_transitions_for_role("Resolved", "staff")
    assert "In Progress" in get_allowed_transitions_for_role("Closed", "staff")

    # Customer allowed next stages
    assert get_allowed_transitions_for_role("Pending", "customer") == ["Pending"]
    assert get_allowed_transitions_for_role("Assigned", "customer") == ["Assigned"]
    assert get_allowed_transitions_for_role("In Progress", "customer") == ["In Progress"]
    assert "Closed" in get_allowed_transitions_for_role("Resolved", "customer")


def test_resolution_tracking_lifecycle_progression(api_client, create_user):
    """Verify full step-by-step transition from Pending to Resolved and Closed."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff_id = create_staff_user(sessions, "Network", "Field Engineer")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Fiber cut",
            description="desc",
            status="Pending",
        )
        session.add(complaint)
        session.commit()

        staff_user = session.get(User, staff_id)

        # 1. Pending -> Assigned
        transition_complaint_status(session, complaint, "Assigned", staff_user)
        assert complaint.status == "Assigned"

        # 2. Assigned -> In Progress
        transition_complaint_status(session, complaint, "In Progress", staff_user)
        assert complaint.status == "In Progress"

        # 3. In Progress -> Resolved with resolution notes
        transition_complaint_status(
            session,
            complaint,
            "Resolved",
            staff_user,
            resolution_notes="Fiber line spliced and optical power restored.",
        )
        assert complaint.status == "Resolved"
        if hasattr(complaint, "resolved_at"):
            assert complaint.resolved_at is not None
        if hasattr(complaint, "resolution_notes"):
            assert complaint.resolution_notes == "Fiber line spliced and optical power restored."

        # 4. Resolved -> Closed
        transition_complaint_status(session, complaint, "Closed", staff_user)
        assert complaint.status == "Closed"


def test_invalid_lifecycle_transition_rejected(api_client, create_user):
    """Staff cannot jump directly from Pending to Resolved or Closed to Pending."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff_id = create_staff_user(sessions, "Billing", "Billing Staff")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Billing Issue",
            subject="Wrong bill",
            description="desc",
            status="Pending",
        )
        session.add(complaint)
        session.commit()

        staff_user = session.get(User, staff_id)

        # Direct Pending -> Resolved is illegal
        with pytest.raises(HTTPException) as exc_info:
            transition_complaint_status(session, complaint, "Resolved", staff_user)
        assert exc_info.value.status_code == 400


def test_customer_cannot_mark_complaint_resolved(api_client, create_user):
    """Customer is not permitted to mark complaints resolved or assigned."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="No signal",
            description="desc",
            status="In Progress",
        )
        session.add(complaint)
        session.commit()

        customer_user = session.get(User, customer_id)

        with pytest.raises(HTTPException) as exc_info:
            transition_complaint_status(session, complaint, "Resolved", customer_user)
        assert exc_info.value.status_code == 403


def test_customer_can_close_their_own_resolved_complaint(api_client, create_user):
    """Customer can confirm closure when their complaint is in Resolved state."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Signal fixed",
            description="desc",
            status="Resolved",
        )
        session.add(complaint)
        session.commit()

        customer_user = session.get(User, customer_id)
        transition_complaint_status(session, complaint, "Closed", customer_user)
        assert complaint.status == "Closed"


def test_customer_cannot_close_other_customers_complaint(api_client, create_user):
    """Customer cannot modify complaints belonging to another customer."""
    _, sessions = api_client
    owner_id, _ = create_user(sessions, "customer")
    other_customer_id, _ = create_user(sessions, "customer")

    with sessions() as session:
        complaint = Complaint(
            customer_id=owner_id,
            complaint_type="Network Issue",
            subject="Owner's issue",
            description="desc",
            status="Resolved",
        )
        session.add(complaint)
        session.commit()

        other_user = session.get(User, other_customer_id)
        with pytest.raises(HTTPException) as exc_info:
            transition_complaint_status(session, complaint, "Closed", other_user)
        assert exc_info.value.status_code == 403


def test_reopening_resolved_complaint_clears_resolution_timestamp(api_client, create_user):
    """Moving a complaint from Resolved back to In Progress clears the resolved_at timestamp."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff_id = create_staff_user(sessions, "Technical", "Tech Support")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Technical Issue",
            subject="Modem issue",
            description="desc",
            status="In Progress",
        )
        session.add(complaint)
        session.commit()

        staff_user = session.get(User, staff_id)

        # Mark resolved
        transition_complaint_status(session, complaint, "Resolved", staff_user)
        assert complaint.status == "Resolved"

        # Reopen complaint: Resolved -> In Progress
        transition_complaint_status(session, complaint, "In Progress", staff_user)
        assert complaint.status == "In Progress"
        if hasattr(complaint, "resolved_at"):
            assert complaint.resolved_at is None


def test_api_get_complaint_by_id_access_control(api_client, create_user, auth_headers):
    """API endpoint GET /api/complaints/{id} enforces ownership for customers and allows staff."""
    client, sessions = api_client
    owner_id, _ = create_user(sessions, "customer")
    other_customer_id, _ = create_user(sessions, "customer")
    staff_id = create_staff_user(sessions, "Network", "Network Specialist")

    with sessions() as session:
        complaint = Complaint(
            customer_id=owner_id,
            complaint_type="Network Issue",
            subject="Test Network",
            description="Detail",
            status="In Progress",
            department="Network",
            assigned_to=staff_id,
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # 1. Owner can access their complaint
    res_owner = client.get(
        f"/api/complaints/{complaint_id}",
        headers=auth_headers(owner_id),
    )
    assert res_owner.status_code == 200
    assert res_owner.json()["id"] == complaint_id
    assert res_owner.json()["customer_id"] == owner_id
    assert res_owner.json()["department"] == "Network"

    # 2. Other customer is forbidden
    res_other = client.get(
        f"/api/complaints/{complaint_id}",
        headers=auth_headers(other_customer_id),
    )
    assert res_other.status_code == 403

    # 3. Staff can access any complaint
    res_staff = client.get(
        f"/api/complaints/{complaint_id}",
        headers=auth_headers(staff_id),
    )
    assert res_staff.status_code == 200
    assert res_staff.json()["id"] == complaint_id

    # 4. Nonexistent complaint returns 404
    res_404 = client.get(
        "/api/complaints/99999",
        headers=auth_headers(staff_id),
    )
    assert res_404.status_code == 404


def test_api_complaint_submission_auto_assignment_flow(api_client, create_user, auth_headers):
    """Submitting a complaint via API triggers automatic routing and least-loaded staff assignment."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff1_id = create_staff_user(sessions, "Billing", "Billing Rep 1")
    staff2_id = create_staff_user(sessions, "Billing", "Billing Rep 2")

    with sessions() as session:
        # Give staff1 an active task so staff2 is less loaded
        existing = Complaint(
            customer_id=customer_id,
            complaint_type="Billing Issue",
            subject="Prior task",
            description="desc",
            department="Billing",
            status="Assigned",
            assigned_to=staff1_id,
        )
        session.add(existing)
        session.commit()

    # Submit new billing complaint
    res = client.post(
        "/api/complaints/",
        headers=auth_headers(customer_id),
        json={
            "complaint_type": "Billing Issue",
            "subject": "Incorrect tax charges",
            "description": "Billed extra GST",
            "priority": "High",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "Assigned"
    assert data["department"] == "Billing"
    assert data["assigned_to"] == staff2_id


def test_api_status_transition_with_resolution_notes(api_client, create_user, auth_headers):
    """Staff updates complaint to Resolved with resolution notes; customer then closes it."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff_id = create_staff_user(sessions, "Technical", "Fiber Tech")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Technical Issue",
            subject="ONT red light",
            description="desc",
            status="In Progress",
            department="Technical",
            assigned_to=staff_id,
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # Staff marks complaint Resolved with resolution notes
    res_resolve = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(staff_id),
        json={
            "status": "Resolved",
            "resolution_notes": "Re-crimped fiber connector at customer premises.",
        },
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "Resolved"
    assert res_resolve.json()["resolved_at"] is not None
    assert res_resolve.json()["resolution_notes"] == "Re-crimped fiber connector at customer premises."

    # Customer confirms closure: Resolved -> Closed
    res_close = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(customer_id),
        json={"status": "Closed"},
    )
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "Closed"


def test_reopening_from_closed_clears_resolution_timestamp(api_client, create_user):
    """Fix H-1: Reopening a complaint from Closed back to In Progress clears resolved_at."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff_id = create_staff_user(sessions, "Network", "Network Eng")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Router issue",
            description="desc",
            status="In Progress",
            department="Network",
            assigned_to=staff_id,
        )
        session.add(complaint)
        session.commit()

        staff_user = session.get(User, staff_id)

        # 1. Resolve: In Progress -> Resolved
        transition_complaint_status(session, complaint, "Resolved", staff_user)
        assert complaint.status == "Resolved"
        assert complaint.resolved_at is not None

        # 2. Close: Resolved -> Closed
        transition_complaint_status(session, complaint, "Closed", staff_user)
        assert complaint.status == "Closed"
        assert complaint.resolved_at is not None  # Preserves resolution time while closed

        # 3. Reopen: Closed -> In Progress
        transition_complaint_status(session, complaint, "In Progress", staff_user)
        assert complaint.status == "In Progress"
        assert complaint.resolved_at is None  # Timestamp must be cleared when active again


def test_auto_assignment_protects_assigned_status_and_assigned_to(api_client, create_user):
    """Fix H-2: auto_assign_complaint must not reassign already assigned complaints unless force=True."""
    _, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff1_id = create_staff_user(sessions, "Network", "Agent Alpha")
    staff2_id = create_staff_user(sessions, "Network", "Agent Beta")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Network problem",
            description="desc",
            department="Network",
            status="Assigned",
            assigned_to=staff1_id,
        )
        session.add(complaint)
        session.commit()

        # Without force: should return complaint unchanged (keeping staff1_id)
        result = auto_assign_complaint(session, complaint, force=False)
        assert result.assigned_to == staff1_id
        assert result.status == "Assigned"

        # Give staff1 a workload, making staff2 the least loaded
        staff2_workload = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Workload",
            description="desc",
            department="Network",
            status="Assigned",
            assigned_to=staff1_id,
        )
        session.add(staff2_workload)
        session.commit()

        # With force=True: intentional reassignment should occur (assigning to staff2_id)
        reassigned = auto_assign_complaint(session, complaint, force=True)
        assert reassigned.assigned_to == staff2_id
        assert reassigned.status == "Assigned"


def test_department_aware_staff_permissions_permitted_and_rejected(api_client, create_user, auth_headers):
    """Fix M-1: Staff can manage complaints in their own department, but cross-department actions are rejected."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    network_staff_id = create_staff_user(sessions, "Network", "Network Specialist")
    billing_staff_id = create_staff_user(sessions, "Billing", "Billing Specialist")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Packet loss",
            description="desc",
            status="In Progress",
            department="Network",
            assigned_to=network_staff_id,
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # 1. Billing staff attempts cross-department transition on Network complaint -> 403 Forbidden
    res_rejected = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(billing_staff_id),
        json={"status": "Resolved", "resolution_notes": "Attempted by wrong department"},
    )
    assert res_rejected.status_code == 403
    assert "cannot modify complaints belonging to" in res_rejected.json()["detail"]

    # 2. Network staff performs same-department transition -> 200 OK
    res_permitted = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(network_staff_id),
        json={"status": "Resolved", "resolution_notes": "Fixed by Network team"},
    )
    assert res_permitted.status_code == 200
    assert res_permitted.json()["status"] == "Resolved"


def test_cross_department_reassignment_rejection(api_client, create_user, auth_headers):
    """Fix M-1: Staff cannot reassign complaints of another department, or assign staff to wrong department."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    network_staff_id = create_staff_user(sessions, "Network", "Net Rep")
    billing_staff_id = create_staff_user(sessions, "Billing", "Bill Rep")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Fiber cut",
            description="desc",
            status="Pending",
            department="Network",
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # Billing staff cannot reassign a Network complaint -> 403
    res_cross_reassign = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(billing_staff_id),
        json={"assigned_to": billing_staff_id, "department": "Network"},
    )
    assert res_cross_reassign.status_code == 403

    # Network staff cannot assign a Billing staff member to Network department -> 400
    res_mismatched_worker = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(network_staff_id),
        json={"assigned_to": billing_staff_id, "department": "Network"},
    )
    assert res_mismatched_worker.status_code == 400
    assert "cannot assign to" in res_mismatched_worker.json()["detail"]


def test_api_status_update_returns_updated_at(api_client, create_user, auth_headers):
    """Fix L-1: update_complaint_status response includes the updated_at timestamp."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    staff_id = create_staff_user(sessions, "Network", "Ops Lead")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Latency spike",
            description="desc",
            status="In Progress",
            department="Network",
            assigned_to=staff_id,
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    res = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(staff_id),
        json={"status": "Resolved", "resolution_notes": "Routing table restored"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "updated_at" in data
    assert data["updated_at"] is not None


def test_network_staff_cannot_transfer_complaint_to_billing(api_client, create_user, auth_headers):
    """Fix 1: Network staff cannot transfer a complaint to Billing."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    network_staff_id = create_staff_user(sessions, "Network", "Net Staff")
    billing_staff_id = create_staff_user(sessions, "Billing", "Bill Staff")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Router down",
            description="desc",
            department="Network",
            status="Pending",
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # Network staff attempts to transfer the complaint to Billing department -> 403
    res = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(network_staff_id),
        json={"assigned_to": billing_staff_id, "department": "Billing"},
    )
    assert res.status_code == 403
    assert "cannot transfer complaints to" in res.json()["detail"]


def test_staff_with_no_department_cannot_modify_named_department_complaint(
    api_client, create_user, auth_headers
):
    """Fix 2: Staff with department=None cannot modify or reassign a complaint with a named department."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    unassigned_staff_id, _ = create_user(sessions, "staff")  # department is None
    network_staff_id = create_staff_user(sessions, "Network", "Network Specialist")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Fiber cut",
            description="desc",
            department="Network",
            status="In Progress",
            assigned_to=network_staff_id,
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # 1. Unassigned staff cannot update status of a Network complaint
    res_status = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(unassigned_staff_id),
        json={"status": "Resolved", "resolution_notes": "Attempted without department"},
    )
    assert res_status.status_code == 403
    assert "without an assigned department cannot modify" in res_status.json()["detail"]

    # 2. Unassigned staff cannot reassign a Network complaint
    res_assign = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(unassigned_staff_id),
        json={"assigned_to": network_staff_id, "department": "Network"},
    )
    assert res_assign.status_code == 403
    assert "without an assigned department cannot reassign" in res_assign.json()["detail"]


def test_staff_with_no_department_can_triage_unassigned_complaint(
    api_client, create_user, auth_headers
):
    """Fix 2: Staff with department=None can triage unassigned complaints."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    unassigned_staff_id, _ = create_user(sessions, "staff")  # department is None
    network_staff_id = create_staff_user(sessions, "Network", "Network Tech")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Other",
            subject="Uncategorized issue",
            description="desc",
            department=None,
            status="Pending",
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # Unassigned staff triages the unassigned complaint by assigning it to Network
    res = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(unassigned_staff_id),
        json={"assigned_to": network_staff_id, "department": "Network"},
    )
    assert res.status_code == 200
    assert res.json()["department"] == "Network"
    assert res.json()["assigned_to"] == network_staff_id
    assert res.json()["status"] == "Assigned"


def test_assignee_cannot_bypass_department_restrictions(
    api_client, create_user, auth_headers
):
    """Fix 3: Being the current assignee does not grant permission to act outside the staff member's department."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    billing_staff_id = create_staff_user(sessions, "Billing", "Billing Agent")
    network_staff_id = create_staff_user(sessions, "Network", "Network Agent")

    with sessions() as session:
        # A Network complaint where assigned_to is billing_staff_id
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Misassigned complaint",
            description="desc",
            department="Network",
            status="In Progress",
            assigned_to=billing_staff_id,
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # Billing staff (even though complaint.assigned_to == billing_staff_id) cannot modify status
    res_status = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(billing_staff_id),
        json={"status": "Resolved", "resolution_notes": "Cross-department bypass attempt"},
    )
    assert res_status.status_code == 403
    assert "cannot modify complaints belonging to" in res_status.json()["detail"]

    # Billing staff cannot reassign this Network complaint
    res_assign = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(billing_staff_id),
        json={"assigned_to": network_staff_id, "department": "Network"},
    )
    assert res_assign.status_code == 403
    assert "cannot reassign complaints belonging to" in res_assign.json()["detail"]


def test_same_department_assignment_and_status_transitions_succeed(
    api_client, create_user, auth_headers
):
    """Legitimate same-department assignments and status transitions continue to work."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    tech_staff_1 = create_staff_user(sessions, "Technical", "Tech Lead")
    tech_staff_2 = create_staff_user(sessions, "Technical", "Tech Worker")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Technical Issue",
            subject="Router config",
            description="desc",
            department="Technical",
            status="Pending",
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # 1. Tech staff 1 assigns complaint to Tech staff 2
    res_assign = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(tech_staff_1),
        json={"assigned_to": tech_staff_2, "department": "Technical"},
    )
    assert res_assign.status_code == 200
    assert res_assign.json()["assigned_to"] == tech_staff_2
    assert res_assign.json()["status"] == "Assigned"

    # 2. Tech staff 2 transitions to In Progress
    res_progress = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(tech_staff_2),
        json={"status": "In Progress"},
    )
    assert res_progress.status_code == 200
    assert res_progress.json()["status"] == "In Progress"

    # 3. Tech staff 2 marks Resolved
    res_resolve = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(tech_staff_2),
        json={"status": "Resolved", "resolution_notes": "Firmware updated"},
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "Resolved"
    assert res_resolve.json()["resolved_at"] is not None


def test_customers_remain_restricted_to_own_complaints(
    api_client, create_user, auth_headers
):
    """Customers cannot access or modify complaints belonging to another customer."""
    client, sessions = api_client
    customer_a_id, _ = create_user(sessions, "customer")
    customer_b_id, _ = create_user(sessions, "customer")

    with sessions() as session:
        complaint = Complaint(
            customer_id=customer_a_id,
            complaint_type="Network Issue",
            subject="Customer A private ticket",
            description="desc",
            department="Network",
            status="Resolved",
        )
        session.add(complaint)
        session.commit()
        complaint_id = complaint.id

    # 1. Customer B cannot view Customer A's complaint
    res_view = client.get(
        f"/api/complaints/{complaint_id}",
        headers=auth_headers(customer_b_id),
    )
    assert res_view.status_code == 403

    # 2. Customer B cannot close Customer A's complaint
    res_close = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(customer_b_id),
        json={"status": "Closed"},
    )
    assert res_close.status_code == 403

    # 3. Customer A can view their own complaint
    res_owner_view = client.get(
        f"/api/complaints/{complaint_id}",
        headers=auth_headers(customer_a_id),
    )
    assert res_owner_view.status_code == 200
    assert res_owner_view.json()["id"] == complaint_id

    # 4. Customer A can close their own resolved complaint
    res_owner_close = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=auth_headers(customer_a_id),
        json={"status": "Closed"},
    )
    assert res_owner_close.status_code == 200
    assert res_owner_close.json()["status"] == "Closed"



