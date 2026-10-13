import pytest

from app.models.models import Complaint


def insert_complaint(session_factory, customer_id, subject="Test complaint"):
    complaint = Complaint(
        customer_id=customer_id,
        complaint_type="Network Issue",
        subject=subject,
        description="Test description",
        priority="Medium",
        status="Pending",
    )
    with session_factory() as session:
        session.add(complaint)
        session.commit()
        session.refresh(complaint)
        return complaint.id


def test_submit_and_list_my_complaints_without_login(api_client):
    client, _ = api_client

    response = client.post(
        "/api/complaints/",
        json={
            "complaint_type": "Network Issue",
            "subject": "No login needed",
            "description": "Submitted as the shared guest customer",
        },
    )
    assert response.status_code == 200
    created_id = response.json()["complaint_id"]

    mine = client.get("/api/complaints/my")
    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()] == [created_id]


def test_customer_cannot_submit_unsupported_priority(api_client):
    client, _ = api_client

    response = client.post(
        "/api/complaints/",
        json={
            "complaint_type": "Network Issue",
            "subject": "Invalid priority",
            "description": "Priority must match the database enum",
            "priority": "Urgent",
        },
    )

    assert response.status_code == 422


def test_company_endpoints_are_open(api_client, create_user):
    client, sessions = api_client
    customer_id = create_user(sessions, "customer")
    first_id = insert_complaint(sessions, customer_id, "First")
    second_id = insert_complaint(sessions, customer_id, "Second")

    response = client.get("/api/complaints/")
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {first_id, second_id}
    for path in (
        "/api/complaints/summary",
        "/api/complaints/staff",
        "/api/complaints/departments",
        "/api/network/measurements",
        "/api/network/map-data",
    ):
        assert client.get(path).status_code == 200, path


def test_assign_valid_staff_member(api_client, create_user):
    client, sessions = api_client
    assignee_id = create_user(sessions, "staff")
    customer_id = create_user(sessions, "customer")
    complaint_id = insert_complaint(sessions, customer_id)

    response = client.put(
        f"/api/complaints/{complaint_id}/assign",
        json={"assigned_to": assignee_id, "department": "Network"},
    )

    assert response.status_code == 200
    assert response.json()["assigned_to"] == assignee_id
    assert response.json()["status"] == "Assigned"


def test_assignment_rejects_invalid_assignee_department_and_complaint(
    api_client, create_user
):
    client, sessions = api_client
    staff_id = create_user(sessions, "staff")
    customer_id = create_user(sessions, "customer")
    complaint_id = insert_complaint(sessions, customer_id)

    wrong_role = client.put(
        f"/api/complaints/{complaint_id}/assign",
        json={"assigned_to": customer_id, "department": "Network"},
    )
    missing_assignee = client.put(
        f"/api/complaints/{complaint_id}/assign",
        json={"assigned_to": 99999, "department": "Network"},
    )
    invalid_department = client.put(
        f"/api/complaints/{complaint_id}/assign",
        json={"assigned_to": staff_id, "department": "Unlisted"},
    )
    missing_complaint = client.put(
        "/api/complaints/99999/assign",
        json={"assigned_to": staff_id, "department": "Network"},
    )

    assert wrong_role.status_code == 400
    assert missing_assignee.status_code == 404
    assert invalid_department.status_code == 400
    assert missing_complaint.status_code == 404


def test_status_update_rejects_invalid_status_and_missing_complaint(
    api_client, create_user
):
    client, sessions = api_client
    customer_id = create_user(sessions, "customer")
    complaint_id = insert_complaint(sessions, customer_id)

    successful_update = client.put(
        f"/api/complaints/{complaint_id}/status", json={"status": "In Progress"}
    )
    invalid_status = client.put(
        f"/api/complaints/{complaint_id}/status", json={"status": "Unknown"}
    )
    missing_complaint = client.put(
        "/api/complaints/99999/status", json={"status": "Pending"}
    )

    assert successful_update.status_code == 200
    assert successful_update.json()["status"] == "In Progress"
    assert invalid_status.status_code == 400
    assert missing_complaint.status_code == 404
