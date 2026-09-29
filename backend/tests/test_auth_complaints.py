import base64
import hashlib
import hmac
import json
import os
import time

import pytest

from app.auth import _encode_segment
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


def expired_token(user_id):
    header = _encode_segment({"alg": "HS256", "typ": "JWT"})
    payload = _encode_segment({"sub": str(user_id), "exp": int(time.time()) - 60})
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(
        os.environ["JWT_SECRET"].encode(), signing_input, hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{encoded_signature}"


def test_login_accepts_valid_credentials(api_client, create_user):
    client, sessions = api_client
    user_id, password = create_user(sessions, "customer")

    with sessions() as session:
        from app.models.models import User

        email = session.query(User.email).filter(User.id == user_id).scalar()

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200
    assert response.json()["user"] == {"id": user_id, "role": "customer"}
    assert response.json()["token_type"] == "bearer"


def test_login_rejects_invalid_password(api_client, create_user):
    client, sessions = api_client
    create_user(sessions, "customer", email="customer@example.invalid")

    response = client.post(
        "/api/auth/login",
        json={"email": "customer@example.invalid", "password": "wrong"},
    )

    assert response.status_code == 401


def test_expired_jwt_is_rejected(api_client, create_user):
    client, sessions = api_client
    user_id, _ = create_user(sessions, "customer")

    response = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {expired_token(user_id)}"},
    )

    assert response.status_code == 401


def test_customer_create_uses_jwt_owner_and_my_list_is_scoped(
    api_client, create_user, auth_headers
):
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    other_customer_id, _ = create_user(sessions, "customer")
    other_complaint_id = insert_complaint(sessions, other_customer_id, "Other user")

    response = client.post(
        "/api/complaints/",
        headers=auth_headers(customer_id),
        json={
            "customer_id": other_customer_id,
            "complaint_type": "Network Issue",
            "subject": "Owned by authenticated user",
            "description": "Ownership comes from the JWT",
        },
    )

    assert response.status_code == 200
    created_id = response.json()["complaint_id"]
    with sessions() as session:
        created = session.get(Complaint, created_id)
        assert created.customer_id == customer_id

    response = client.get("/api/complaints/my", headers=auth_headers(customer_id))
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [created_id]
    assert other_complaint_id not in [item["id"] for item in response.json()]


def test_customer_cannot_submit_unsupported_priority(api_client, create_user, auth_headers):
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")

    response = client.post(
        "/api/complaints/",
        headers=auth_headers(customer_id),
        json={
            "complaint_type": "Network Issue",
            "subject": "Invalid priority",
            "description": "Priority must match the database enum",
            "priority": "Urgent",
        },
    )

    assert response.status_code == 422


def test_staff_can_view_all_complaints(api_client, create_user, auth_headers):
    client, sessions = api_client
    staff_id, _ = create_user(sessions, "staff")
    customer_id, _ = create_user(sessions, "customer")
    first_id = insert_complaint(sessions, customer_id, "First")
    second_id = insert_complaint(sessions, customer_id, "Second")

    response = client.get("/api/complaints/", headers=auth_headers(staff_id))

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {first_id, second_id}
    assert client.get(
        "/api/complaints/summary", headers=auth_headers(staff_id)
    ).status_code == 200
    staff_response = client.get(
        "/api/complaints/staff", headers=auth_headers(staff_id)
    )
    assert staff_response.status_code == 200
    assert any(item["id"] == staff_id for item in staff_response.json())
    assert client.get(
        "/api/network/measurements", headers=auth_headers(staff_id)
    ).status_code == 200
    assert client.get(
        "/api/network/map-data", headers=auth_headers(staff_id)
    ).status_code == 200


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/complaints/"),
        ("get", "/api/complaints/summary"),
        ("get", "/api/complaints/staff"),
        ("get", "/api/network/measurements"),
        ("get", "/api/network/map-data"),
    ],
)
def test_customer_cannot_use_staff_endpoints(
    api_client, create_user, auth_headers, method, path
):
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")

    response = getattr(client, method)(path, headers=auth_headers(customer_id))

    assert response.status_code == 403


def test_customer_cannot_assign_or_update_complaints(
    api_client, create_user, auth_headers
):
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    headers = auth_headers(customer_id)

    assignment = client.put(
        "/api/complaints/1/assign",
        headers=headers,
        json={"assigned_to": 2, "department": "Network"},
    )
    status_update = client.put(
        "/api/complaints/1/status",
        headers=headers,
        json={"status": "Resolved"},
    )

    assert assignment.status_code == 403
    assert status_update.status_code == 403


def test_staff_can_assign_valid_staff_member(api_client, create_user, auth_headers):
    client, sessions = api_client
    staff_id, _ = create_user(sessions, "staff")
    assignee_id, _ = create_user(sessions, "staff")
    customer_id, _ = create_user(sessions, "customer")
    complaint_id = insert_complaint(sessions, customer_id)

    response = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(staff_id),
        json={"assigned_to": assignee_id, "department": "Network"},
    )

    assert response.status_code == 200
    assert response.json()["assigned_to"] == assignee_id
    assert response.json()["status"] == "Assigned"


def test_assignment_rejects_invalid_assignee_department_and_complaint(
    api_client, create_user, auth_headers
):
    client, sessions = api_client
    staff_id, _ = create_user(sessions, "staff")
    customer_id, _ = create_user(sessions, "customer")
    complaint_id = insert_complaint(sessions, customer_id)
    headers = auth_headers(staff_id)

    wrong_role_id, _ = create_user(sessions, "customer")
    wrong_role = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=headers,
        json={"assigned_to": wrong_role_id, "department": "Network"},
    )
    missing_assignee = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=headers,
        json={"assigned_to": 99999, "department": "Network"},
    )
    invalid_department = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=headers,
        json={"assigned_to": staff_id, "department": "Unlisted"},
    )
    missing_complaint = client.put(
        "/api/complaints/99999/assign",
        headers=headers,
        json={"assigned_to": staff_id, "department": "Network"},
    )

    assert wrong_role.status_code == 400
    assert missing_assignee.status_code == 404
    assert invalid_department.status_code == 400
    assert missing_complaint.status_code == 404


def test_status_update_rejects_invalid_status_and_missing_complaint(
    api_client, create_user, auth_headers
):
    client, sessions = api_client
    staff_id, _ = create_user(sessions, "staff")
    customer_id, _ = create_user(sessions, "customer")
    complaint_id = insert_complaint(sessions, customer_id)
    headers = auth_headers(staff_id)

    successful_update = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=headers,
        json={"status": "In Progress"},
    )
    invalid_status = client.put(
        f"/api/complaints/{complaint_id}/status",
        headers=headers,
        json={"status": "Unknown"},
    )
    missing_complaint = client.put(
        "/api/complaints/99999/status",
        headers=headers,
        json={"status": "Pending"},
    )

    assert successful_update.status_code == 200
    assert successful_update.json()["status"] == "In Progress"
    assert invalid_status.status_code == 400
    assert missing_complaint.status_code == 404