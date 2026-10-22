from unittest.mock import MagicMock, patch
import pytest

from app.api.chatbot import execute_tool
from app.models.models import Complaint, NetworkMeasurement, User


def test_chatbot_config(api_client):
    client, _ = api_client
    response = client.get("/api/chatbot/config")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "status" in data
    assert data["assistant_name"] == "Telecom AI Assistant"
    assert len(data["supported_features"]) > 0


def test_chatbot_empty_message(api_client):
    client, _ = api_client
    response = client.post("/api/chatbot/message", json={"message": "   "})
    assert response.status_code == 400


def test_chatbot_unconfigured_key(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.setenv("GROQ_API_KEY", "PASTE_YOUR_NEW_GROQ_API_KEY_HERE")
    response = client.post(
        "/api/chatbot/message",
        json={"message": "My internet is very slow today"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unconfigured"
    assert "Groq API key" in data["response"]


def test_chatbot_tool_network_status(api_client):
    _, session_factory = api_client
    with session_factory() as db:
        # Add sample measurement
        from datetime import datetime
        meas = NetworkMeasurement(
            operator="Airtel",
            timestamp=datetime.utcnow(),
            latitude=28.6139,
            longitude=77.2090,
            download_mbps=45.2,
            upload_mbps=12.1,
            rtt_ms=38.5,
            network_technology="5G",
        )
        db.add(meas)
        db.commit()

        result = execute_tool("check_network_status", {"operator": "Airtel"}, db, None)
        assert result["network_status"] in ("Normal", "Degraded")
        assert result["average_latency_ms"] == 38.5
        assert "Airtel" in result["monitored_operators"]


def test_chatbot_tool_plans_honesty(api_client):
    _, session_factory = api_client
    with session_factory() as db:
        result = execute_tool("get_telecom_plans", {}, db, None)
        assert result["available"] is False
        assert "not managed" in result["message"]


def test_chatbot_tool_complaint_lifecycle(api_client, create_user):
    _, session_factory = api_client
    user_id, _ = create_user(session_factory, role="customer")

    with session_factory() as db:
        user = db.query(User).filter(User.id == user_id).first()

        # Step 1: Prepare summary
        summary_result = execute_tool(
            "prepare_complaint_summary",
            {
                "complaint_type": "Network Issue",
                "subject": "Frequent call drops",
                "description": "Calls disconnect every 2 minutes in my apartment",
                "priority": "High",
            },
            db,
            user,
        )
        assert summary_result["summary"]["complaint_type"] == "Network Issue"
        assert "explicit confirmation" in summary_result["instruction"]

        # Step 2: Unauthenticated submission fails safely
        guest_sub = execute_tool(
            "submit_confirmed_complaint",
            {
                "complaint_type": "Network Issue",
                "subject": "Frequent call drops",
                "description": "Calls disconnect every 2 minutes in my apartment",
            },
            db,
            None,
        )
        assert guest_sub["success"] is False
        assert "Authentication required" in guest_sub["error"]

        # Step 3: Authenticated customer submits
        sub_result = execute_tool(
            "submit_confirmed_complaint",
            {
                "complaint_type": "Network Issue",
                "subject": "Frequent call drops",
                "description": "Calls disconnect every 2 minutes in my apartment",
                "priority": "High",
            },
            db,
            user,
        )
        assert sub_result["success"] is True
        cid = sub_result["complaint_id"]
        assert cid > 0
        assert sub_result["department"] == "Network"

        # Step 4: Lookup complaint by ID
        lookup = execute_tool("get_complaint_by_id", {"complaint_id": cid}, db, user)
        assert lookup["found"] is True
        assert lookup["subject"] == "Frequent call drops"
        assert lookup["department"] == "Network"

        # Step 5: Customer complaint listing
        my_list = execute_tool("get_customer_complaints", {}, db, user)
        assert my_list["authenticated"] is True
        assert my_list["count"] >= 1
        assert my_list["complaints"][0]["id"] == cid


def test_chatbot_with_mocked_groq(api_client, monkeypatch):
    client, _ = api_client
    monkeypatch.setenv("GROQ_API_KEY", "gsk_mock_valid_key_for_testing_123456789")

    mock_choice = MagicMock()
    mock_choice.message.tool_calls = None
    mock_choice.message.content = "Here are 3 steps to fix slow mobile data: 1. Toggle airplane mode. 2. Verify APN settings. 3. Check data limit."

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch("groq.Groq") as mock_groq_class:
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.return_value = mock_completion
        mock_groq_class.return_value = mock_instance

        response = client.post(
            "/api/chatbot/message",
            json={
                "message": "Why is my 5G data running slow?",
                "conversation_history": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Toggle airplane mode" in data["response"]


def test_chatbot_groq_auth_error(api_client, monkeypatch):
    from groq import AuthenticationError

    client, _ = api_client
    monkeypatch.setenv("GROQ_API_KEY", "gsk_invalid_key_value")

    with patch("groq.Groq") as mock_groq_class:
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.side_effect = AuthenticationError(
            message="Invalid API Key", response=MagicMock(status_code=401), body={}
        )
        mock_groq_class.return_value = mock_instance

        response = client.post(
            "/api/chatbot/message",
            json={"message": "Hello"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "auth_error"
        assert "Authentication failed" in data["response"]


def test_chatbot_groq_rate_limit_error(api_client, monkeypatch):
    from groq import RateLimitError

    client, _ = api_client
    monkeypatch.setenv("GROQ_API_KEY", "gsk_valid_key_value")

    with patch("groq.Groq") as mock_groq_class:
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit reached", response=MagicMock(status_code=429), body={}
        )
        mock_groq_class.return_value = mock_instance

        response = client.post(
            "/api/chatbot/message",
            json={"message": "Hello"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rate_limit"
        assert "rate limit" in data["response"]


def test_chatbot_tool_network_status_null_operator(api_client):
    _, session_factory = api_client
    with session_factory() as db:
        from datetime import datetime
        meas = NetworkMeasurement(
            operator="Jio",
            timestamp=datetime.utcnow(),
            latitude=19.0760,
            longitude=72.8777,
            download_mbps=55.0,
            upload_mbps=20.0,
            rtt_ms=25.0,
            network_technology="5G",
        )
        db.add(meas)
        db.commit()

        # Test operator is None
        result_none = execute_tool("check_network_status", {"operator": None}, db, None)
        assert result_none["network_status"] in ("Normal", "Degraded")
        assert result_none["recent_telemetry_samples"] >= 1

        # Test operator is string "null"
        result_str_null = execute_tool("check_network_status", {"operator": "null"}, db, None)
        assert result_str_null["network_status"] in ("Normal", "Degraded")
        assert result_str_null["recent_telemetry_samples"] >= 1


def test_chatbot_tool_schema_allows_null():
    from app.api.chatbot import CHATBOT_TOOLS, DEFAULT_MODEL
    assert DEFAULT_MODEL == "openai/gpt-oss-120b"
    net_tool = next(t for t in CHATBOT_TOOLS if t["function"]["name"] == "check_network_status")
    op_type = net_tool["function"]["parameters"]["properties"]["operator"]["type"]
    assert "null" in op_type and "string" in op_type

