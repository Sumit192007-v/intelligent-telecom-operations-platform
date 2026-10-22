import pytest
from app.models.models import Complaint, NetworkMeasurement, User
from app.services.complaint_assignment import auto_assign_complaint


def create_employee(session_factory, role, department, name="Test Employee", email=None):
    """Helper to create an employee with specific role and department."""
    import secrets
    import bcrypt

    password = secrets.token_urlsafe(16)
    dept_str = (department or "nodept").lower().replace(" ", "_")
    email = email or f"{secrets.token_hex(6)}_{dept_str}@telecom.test"
    user = User(
        name=name,
        email=email,
        password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode(),
        role=role,
        department=department,
    )
    with session_factory() as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id, password, email


def test_employee_login_returns_department_and_role(api_client):
    """1. A valid employee can log in using the existing company login and receive role & department."""
    client, sessions = api_client
    user_id, password, email = create_employee(
        sessions, role="support_agent", department="Customer Support", name="Sarah Agent"
    )

    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["id"] == user_id
    assert data["user"]["role"] == "support_agent"
    assert data["user"]["department"] == "Customer Support"
    assert data["user"]["name"] == "Sarah Agent"


def test_network_employee_access_boundaries(api_client, auth_headers):
    """2. A Network employee receives Network access and is scoped to Network complaints."""
    client, sessions = api_client
    net_user_id, _, _ = create_employee(
        sessions, role="engineer", department="Network", name="Net Engineer"
    )

    # Can access network measurements
    meas_res = client.get("/api/network/measurements", headers=auth_headers(net_user_id))
    assert meas_res.status_code == 200

    # Can access network map data
    map_res = client.get("/api/network/map-data", headers=auth_headers(net_user_id))
    assert map_res.status_code == 200


def test_technical_employee_access_boundaries(api_client, auth_headers):
    """3. A Technical employee receives Technical access and cannot access Network endpoints."""
    client, sessions = api_client
    tech_user_id, _, _ = create_employee(
        sessions, role="support_agent", department="Technical", name="Tech Support"
    )

    # Cannot access network operations
    res_meas = client.get("/api/network/measurements", headers=auth_headers(tech_user_id))
    assert res_meas.status_code == 403
    assert "restricted to the Network department" in res_meas.json()["detail"]

    # Can access complaints (scoped to Technical)
    comp_res = client.get("/api/complaints/", headers=auth_headers(tech_user_id))
    assert comp_res.status_code == 200


def test_billing_employee_access_boundaries(api_client, auth_headers):
    """4. A Billing employee receives Billing complaints access and is restricted from Network operations."""
    client, sessions = api_client
    billing_user_id, _, _ = create_employee(
        sessions, role="staff", department="Billing", name="Billing Specialist"
    )

    # Cannot access network map data
    res_map = client.get("/api/network/map-data", headers=auth_headers(billing_user_id))
    assert res_map.status_code == 403
    assert "restricted to the Network department" in res_map.json()["detail"]

    # Cannot access network predictions
    res_pred = client.post(
        "/api/predict/",
        headers=auth_headers(billing_user_id),
        json={"operator": "Airtel", "hour": 14, "day_of_week": 2},
    )
    assert res_pred.status_code == 403
    assert "restricted to the Network department" in res_pred.json()["detail"]


def test_customer_support_employee_access_boundaries(api_client, auth_headers):
    """5. A Customer Support employee receives Customer Support access."""
    client, sessions = api_client
    cs_user_id, _, _ = create_employee(
        sessions, role="support_agent", department="Customer Support", name="CS Rep"
    )

    # Scoped complaint summary
    summary_res = client.get("/api/complaints/summary", headers=auth_headers(cs_user_id))
    assert summary_res.status_code == 200
    assert summary_res.json()["department"] == "Customer Support"


def test_employee_cannot_access_other_department_complaints(api_client, auth_headers, create_user):
    """6. An employee cannot access restricted resources belonging to another department."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    net_user_id, _, _ = create_employee(sessions, "engineer", "Network", "Net Eng")
    bill_user_id, _, _ = create_employee(sessions, "staff", "Billing", "Bill Staff")

    with sessions() as session:
        net_complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Cell drop in tower 4",
            description="Tower 4 is dropping calls",
            department="Network",
            status="In Progress",
            assigned_to=net_user_id,
        )
        session.add(net_complaint)
        session.commit()
        net_complaint_id = net_complaint.id

    # Billing staff tries to fetch Network complaint by ID -> 403 Forbidden
    res = client.get(f"/api/complaints/{net_complaint_id}", headers=auth_headers(bill_user_id))
    assert res.status_code == 403
    assert "cannot view complaints belonging to" in res.json()["detail"]

    # Network staff can access it
    res_ok = client.get(f"/api/complaints/{net_complaint_id}", headers=auth_headers(net_user_id))
    assert res_ok.status_code == 200
    assert res_ok.json()["id"] == net_complaint_id


def test_query_param_cannot_bypass_department_authorization(api_client, auth_headers, create_user):
    """7. Changing a frontend department value or URL does not bypass backend authorization."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    bill_user_id, _, _ = create_employee(sessions, "staff", "Billing", "Billing Specialist")

    with sessions() as session:
        session.add(
            Complaint(
                customer_id=customer_id,
                complaint_type="Network Issue",
                subject="Net issue",
                description="desc",
                department="Network",
                status="Pending",
            )
        )
        session.add(
            Complaint(
                customer_id=customer_id,
                complaint_type="Billing Issue",
                subject="Overcharge",
                description="desc",
                department="Billing",
                status="Pending",
            )
        )
        session.commit()

    # Billing staff explicitly requests Network complaints via query param -> 403 Forbidden
    res_bypass = client.get("/api/complaints/?department=Network", headers=auth_headers(bill_user_id))
    assert res_bypass.status_code == 403
    assert "cannot view complaints belonging to" in res_bypass.json()["detail"]

    # Billing staff queries without param -> receives ONLY Billing complaints
    res_normal = client.get("/api/complaints/", headers=auth_headers(bill_user_id))
    assert res_normal.status_code == 200
    for c in res_normal.json():
        assert c["department"] == "Billing"


def test_missing_or_invalid_department_handled_safely(api_client, auth_headers):
    """8. Missing or invalid department assignments are handled safely."""
    client, sessions = api_client
    invalid_dept_user_id, _, _ = create_employee(
        sessions, role="engineer", department="InvalidDept", name="Invalid Employee"
    )

    # Invalid department user blocked from Network operations
    res_meas = client.get("/api/network/measurements", headers=auth_headers(invalid_dept_user_id))
    assert res_meas.status_code == 403


def test_invalid_credentials_rejected(api_client):
    """9. Invalid credentials are rejected with HTTP 401."""
    client, _ = api_client
    res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@telecom.test", "password": "wrongpassword"},
    )
    assert res.status_code == 401


def test_unauthenticated_requests_cannot_access_protected_endpoints(api_client):
    """10. Unauthenticated requests cannot access protected endpoints."""
    client, _ = api_client
    assert client.get("/api/complaints/").status_code == 401
    assert client.get("/api/complaints/summary").status_code == 401
    assert client.get("/api/network/measurements").status_code == 401
    assert client.get("/api/network/map-data").status_code == 401
    assert client.post("/api/predict/", json={}).status_code == 401


def test_manager_cross_department_oversight(api_client, auth_headers, create_user):
    """11. Managers retain authorized operations dashboards and cross-department management features."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    manager_id, _, _ = create_employee(sessions, "manager", "Operations", "Ops Manager")
    net_user_id, _, _ = create_employee(sessions, "engineer", "Network", "Net Eng")
    bill_user_id, _, _ = create_employee(sessions, "staff", "Billing", "Bill Staff")

    with sessions() as session:
        session.add(
            Complaint(
                customer_id=customer_id,
                complaint_type="Network Issue",
                subject="Net issue",
                description="desc",
                department="Network",
                status="Pending",
            )
        )
        session.add(
            Complaint(
                customer_id=customer_id,
                complaint_type="Billing Issue",
                subject="Bill issue",
                description="desc",
                department="Billing",
                status="Pending",
            )
        )
        session.commit()

    # Manager can view all complaints across departments
    res_all = client.get("/api/complaints/", headers=auth_headers(manager_id))
    assert res_all.status_code == 200
    depts = {c["department"] for c in res_all.json()}
    assert "Network" in depts and "Billing" in depts

    # Manager can filter specifically for a department
    res_net = client.get("/api/complaints/?department=Network", headers=auth_headers(manager_id))
    assert res_net.status_code == 200

    # Manager can access Network operations
    assert client.get("/api/network/measurements", headers=auth_headers(manager_id)).status_code == 200
    assert client.get("/api/network/map-data", headers=auth_headers(manager_id)).status_code == 200


def test_missing_department_employee_handled_safely(api_client, auth_headers, create_user):
    """An employee with missing department (None) is safely blocked from managing named department complaints."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    no_dept_id, _, _ = create_employee(
        sessions, role="support_agent", department=None, name="No Dept Agent"
    )

    with sessions() as session:
        comp = Complaint(
            customer_id=customer_id,
            complaint_type="Network Issue",
            subject="Net issue",
            description="desc",
            department="Network",
            status="Pending",
        )
        session.add(comp)
        session.commit()
        comp_id = comp.id

    # Blocked from reassigning a complaint belonging to a named department
    res = client.put(
        f"/api/complaints/{comp_id}/assign",
        headers=auth_headers(no_dept_id),
        json={"assigned_to": no_dept_id, "department": "Network"},
    )
    assert res.status_code == 403
    assert "without an assigned department cannot reassign" in res.json()["detail"]


def test_cross_department_assignment_enforcement(api_client, auth_headers, create_user):
    """Support agents and staff cannot assign complaints outside their authorized department."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")
    tech_agent_id, _, _ = create_employee(sessions, "support_agent", "Technical", "Tech Agent")
    tech_assignee_id, _, _ = create_employee(sessions, "engineer", "Technical", "Tech Eng")
    bill_assignee_id, _, _ = create_employee(sessions, "staff", "Billing", "Bill Staff")

    with sessions() as session:
        tech_complaint = Complaint(
            customer_id=customer_id,
            complaint_type="Broadband Issue",
            subject="Router failure",
            description="Hardware failure",
            department="Technical",
            status="Pending",
        )
        session.add(tech_complaint)
        session.commit()
        complaint_id = tech_complaint.id

    # 1. Tech agent assigning Tech complaint to Tech engineer -> Allowed (200)
    res_ok = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(tech_agent_id),
        json={"assigned_to": tech_assignee_id, "department": "Technical"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["assigned_to"] == tech_assignee_id

    # 2. Tech agent attempting to transfer complaint to Billing department -> Blocked (403)
    res_bad_dept = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(tech_agent_id),
        json={"assigned_to": tech_assignee_id, "department": "Billing"},
    )
    assert res_bad_dept.status_code == 403
    assert "cannot transfer complaints to the 'Billing' department" in res_bad_dept.json()["detail"]

    # 3. Tech agent attempting to assign Tech complaint to Billing staff member -> Rejected (400)
    res_bad_assignee = client.put(
        f"/api/complaints/{complaint_id}/assign",
        headers=auth_headers(tech_agent_id),
        json={"assigned_to": bill_assignee_id, "department": "Technical"},
    )
    assert res_bad_assignee.status_code == 400
    assert "Assignee belongs to department 'Billing'" in res_bad_assignee.json()["detail"]


def test_customer_cannot_access_employee_endpoints(api_client, auth_headers, create_user):
    """Customer role cannot access employee or network operations endpoints."""
    client, sessions = api_client
    customer_id, _ = create_user(sessions, "customer")

    headers = auth_headers(customer_id)
    assert client.get("/api/complaints/", headers=headers).status_code == 403
    assert client.get("/api/network/measurements", headers=headers).status_code == 403
    assert client.get("/api/network/map-data", headers=headers).status_code == 403
    assert client.get("/api/complaints/staff", headers=headers).status_code == 403
    assert client.get("/api/complaints/summary", headers=headers).status_code == 403

