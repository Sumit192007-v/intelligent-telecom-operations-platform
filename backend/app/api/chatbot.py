import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import _decode_access_token
from app.database import get_db
from app.models.models import Complaint, NetworkMeasurement, User
from app.services.complaint_assignment import auto_assign_complaint

logger = logging.getLogger("chatbot")

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_LENGTH = 2000

SYSTEM_PROMPT = """You are the Telecom AI Assistant, a professional, empathetic, and knowledgeable telecom customer support specialist for the Intelligent Telecom Operations Platform.

Your role:
1. Provide practical, accurate, and concise troubleshooting for telecom issues such as:
   - Slow mobile data / slow internet (APN verification, data saver toggles, signal checking, browser cache)
   - Weak signal / no network / emergency calls only (airplane mode toggle, SIM re-insertion, manual network operator search, coverage area)
   - Dropped calls / call quality issues (VoLTE / Wi-Fi calling settings, network congestion)
   - SIM connectivity / activation / eSIM inquiries
   - Network outages and service disruption inquiries
   - Complaint submission and status tracking

Guidelines for conversation:
- Be warm, courteous, and professional.
- Understand informal phrasing, typos, and colloquial language (e.g., "net not working", "slow net", "cant call").
- Always remember the conversation context. NEVER repeat troubleshooting steps the user has stated they already tried (for instance, if they already restarted their device, do not tell them to restart it again).
- Provide step-by-step, actionable advice.
- When answering about network outages, complaints, or plans, USE THE PROVIDED TOOLS to fetch verified application data.
- HONESTY IS PARAMOUNT:
  * Distinguish verified platform data from general telecom advice.
  * Never fabricate outage statuses, fake plan prices, or fake complaint numbers.
  * If a feature (like plan subscription catalog) is not integrated into the system, state that limitation clearly and politely without inventing fake plans.
- COMPLAINT REGISTRATION WORKFLOW:
  1. Carefully understand the user's problem.
  2. Collect required details: complaint type ('Network Issue', 'Internet Issue', 'Call Issue', 'Billing Issue', 'Technical Issue', 'Customer Support Issue'), subject, and clear description.
  3. Call `prepare_complaint_summary` to summarize the ticket.
  4. Ask the customer for explicit confirmation: "Would you like me to submit this official complaint for you now?"
  5. ONLY when the customer confirms ('yes', 'sure', 'please submit', etc.), call `submit_confirmed_complaint`.
  6. Display the actual complaint ID returned by the backend tool. Never make up an ID.
"""

CHATBOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_network_status",
            "description": "Query live network telemetry and reported issues from the platform database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operator": {
                        "type": "string",
                        "description": "Optional operator name to filter (e.g., 'Airtel', 'Jio', 'Vodafone')",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_telecom_plans",
            "description": "Check currently available service and subscription plans.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_complaints",
            "description": "Retrieve complaints submitted by the currently authenticated customer.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_complaint_by_id",
            "description": "Lookup real-time status and details of a complaint by its numeric ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint_id": {
                        "type": "integer",
                        "description": "The numeric ID of the complaint",
                    }
                },
                "required": ["complaint_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_complaint_summary",
            "description": "Prepare a structured complaint summary and instruct the assistant to seek explicit confirmation from the customer before official submission.",
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint_type": {
                        "type": "string",
                        "description": "Type of complaint, e.g., 'Network Issue', 'Internet Issue', 'Call Issue', 'Billing Issue', 'Technical Issue', 'Customer Support Issue'",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Concise summary of the problem",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the customer's problem",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High", "Critical"],
                        "description": "Priority level (default Medium)",
                    },
                },
                "required": ["complaint_type", "subject", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_confirmed_complaint",
            "description": "Submit the verified complaint ticket to the official platform database. MUST ONLY be called AFTER the customer explicitly confirmed the summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint_type": {
                        "type": "string",
                        "description": "Type of complaint",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject of the complaint",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["Low", "Medium", "High", "Critical"],
                    },
                },
                "required": ["complaint_type", "subject", "description"],
            },
        },
    },
]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    conversation_history: List[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    status: str
    model: str
    complaint_created: Optional[Dict[str, Any]] = None


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Extract authenticated user if Bearer token is provided, without throwing 401."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    try:
        user_id = _decode_access_token(token)
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


def execute_tool(
    name: str,
    args: Dict[str, Any],
    db: Session,
    current_user: Optional[User],
) -> Dict[str, Any]:
    """Safely execute registered backend tools with real database models."""
    try:
        if name == "check_network_status":
            operator = args.get("operator")
            query = db.query(NetworkMeasurement)
            if operator:
                query = query.filter(NetworkMeasurement.operator.ilike(f"%{operator}%"))
            measurements = (
                query.order_by(NetworkMeasurement.timestamp.desc()).limit(150).all()
            )

            if measurements:
                latencies = [
                    m.rtt_ms for m in measurements if m.rtt_ms is not None
                ]
                avg_latency = (
                    round(sum(latencies) / len(latencies), 1) if latencies else None
                )
                red_cells = sum(1 for m in measurements if (m.rtt_ms or 0) >= 75)
                operators = list({m.operator for m in measurements if m.operator})
                techs = list(
                    {
                        m.network_technology
                        for m in measurements
                        if m.network_technology
                    }
                )
            else:
                avg_latency = None
                red_cells = 0
                operators = []
                techs = []

            pending_network_complaints = (
                db.query(Complaint)
                .filter(
                    Complaint.status.in_(["Pending", "Assigned", "In Progress"]),
                    Complaint.complaint_type.in_(
                        [
                            "Network Issue",
                            "network issue",
                            "Internet Issue",
                            "internet issue",
                            "Call Issue",
                            "call issue",
                        ]
                    ),
                )
                .count()
            )

            status_text = (
                "Major Outage"
                if red_cells > 30
                else "Degraded"
                if red_cells > 8
                else "Normal"
            )

            return {
                "source": "Platform Database (Verified)",
                "network_status": status_text,
                "average_latency_ms": avg_latency,
                "high_latency_cells_detected": red_cells,
                "recent_telemetry_samples": len(measurements),
                "active_network_complaints": pending_network_complaints,
                "monitored_operators": operators[:4],
                "technologies": techs[:4],
            }

        elif name == "get_telecom_plans":
            return {
                "source": "Platform Database",
                "available": False,
                "message": (
                    "Service and subscription plan catalog is currently not managed "
                    "in this platform database. Honestly inform the customer that plan pricing "
                    "and subscriptions are managed through the sales portal, and do not invent fake plans."
                ),
            }

        elif name == "get_customer_complaints":
            if not current_user:
                return {
                    "authenticated": False,
                    "message": "User is currently not logged in. Ask them to log in to view their submitted tickets.",
                }
            complaints = (
                db.query(Complaint)
                .filter(Complaint.customer_id == current_user.id)
                .order_by(Complaint.created_at.desc())
                .limit(10)
                .all()
            )
            return {
                "source": "Platform Database (Verified)",
                "authenticated": True,
                "customer_name": current_user.name,
                "count": len(complaints),
                "complaints": [
                    {
                        "id": c.id,
                        "complaint_type": c.complaint_type,
                        "subject": c.subject,
                        "status": c.status,
                        "priority": c.priority,
                        "department": c.department,
                        "created_at": (
                            c.created_at.strftime("%Y-%m-%d %H:%M")
                            if c.created_at
                            else None
                        ),
                        "resolved_at": (
                            c.resolved_at.strftime("%Y-%m-%d %H:%M")
                            if c.resolved_at
                            else None
                        ),
                        "resolution_notes": c.resolution_notes,
                    }
                    for c in complaints
                ],
            }

        elif name == "get_complaint_by_id":
            cid = args.get("complaint_id")
            if not cid:
                return {"found": False, "message": "No complaint ID provided."}
            complaint = db.query(Complaint).filter(Complaint.id == cid).first()
            if not complaint:
                return {
                    "source": "Platform Database (Verified)",
                    "found": False,
                    "message": f"Complaint #{cid} was not found in the operations database.",
                }

            if (
                current_user
                and current_user.role == "customer"
                and complaint.customer_id != current_user.id
            ):
                return {
                    "source": "Platform Database (Verified)",
                    "found": False,
                    "message": f"Access denied: Complaint #{cid} belongs to another user account.",
                }

            return {
                "source": "Platform Database (Verified)",
                "found": True,
                "id": complaint.id,
                "complaint_type": complaint.complaint_type,
                "subject": complaint.subject,
                "description": complaint.description,
                "status": complaint.status,
                "priority": complaint.priority,
                "department": complaint.department,
                "created_at": (
                    complaint.created_at.strftime("%Y-%m-%d %H:%M")
                    if complaint.created_at
                    else None
                ),
                "resolved_at": (
                    complaint.resolved_at.strftime("%Y-%m-%d %H:%M")
                    if complaint.resolved_at
                    else None
                ),
                "resolution_notes": complaint.resolution_notes,
            }

        elif name == "prepare_complaint_summary":
            return {
                "summary": {
                    "complaint_type": args.get("complaint_type", "General Issue"),
                    "subject": args.get("subject", ""),
                    "description": args.get("description", ""),
                    "priority": args.get("priority", "Medium"),
                },
                "instruction": (
                    "Summarize these ticket details clearly for the customer. "
                    "Ask for their explicit confirmation before submitting. "
                    "Do NOT call submit_confirmed_complaint until the customer agrees."
                ),
            }

        elif name == "submit_confirmed_complaint":
            if not current_user:
                return {
                    "success": False,
                    "error": "Authentication required. Please log in with your customer account to submit an official complaint ticket.",
                }
            if current_user.role != "customer":
                return {
                    "success": False,
                    "error": f"Users with role '{current_user.role}' cannot submit customer complaints.",
                }

            complaint = Complaint(
                customer_id=current_user.id,
                complaint_type=args.get("complaint_type", "Network Issue"),
                subject=args.get("subject", "Issue reported via AI Assistant"),
                description=args.get("description", "No details provided"),
                priority=args.get("priority", "Medium"),
                status="Pending",
            )
            auto_assign_complaint(db, complaint)
            db.add(complaint)
            db.commit()
            db.refresh(complaint)

            return {
                "source": "Platform Database (Verified)",
                "success": True,
                "complaint_id": complaint.id,
                "status": complaint.status,
                "department": complaint.department,
                "assigned_to": complaint.assigned_to,
                "message": (
                    f"Complaint #{complaint.id} successfully created and automatically assigned "
                    f"to {complaint.department or 'triage team'} with status '{complaint.status}'."
                ),
            }

        return {"error": f"Unknown tool: {name}"}

    except Exception as exc:
        logger.exception("Error executing tool %s: %s", name, exc)
        return {"error": f"Database query failed: {str(exc)}"}


@router.get("/config")
def get_chatbot_config():
    """Return public configuration status of the chatbot service."""
    api_key = os.getenv("GROQ_API_KEY", "")
    configured = bool(
        api_key
        and not api_key.startswith("PASTE_")
        and api_key != "replace-with-your-groq-api-key"
    )
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    return {
        "status": "ready" if configured else "unconfigured",
        "model": model,
        "assistant_name": "Telecom AI Assistant",
        "supported_features": [
            "Network troubleshooting (slow data, no network, dropped calls)",
            "Live network status & outage verification",
            "Complaint tracking & verified registration",
            "Telecom general assistance",
        ],
    }


@router.post("/message", response_model=ChatResponse)
def handle_chat_message(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Process natural language chatbot queries via Groq LLM with telecom tool calling."""
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty",
        )

    groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
    groq_model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    # Graceful handling when key is not configured or placeholder
    if (
        not groq_api_key
        or groq_api_key.startswith("PASTE_")
        or groq_api_key == "replace-with-your-groq-api-key"
    ):
        return ChatResponse(
            response=(
                "Hello! I am your **Telecom AI Assistant**.\n\n"
                "The system is currently waiting for a valid Groq API key. "
                "To activate live natural-language intelligence powered by Groq, please configure your "
                "`GROQ_API_KEY` in `backend/.env`.\n\n"
                "All existing telecom operations features—network maps, complaint filing, and dashboards—remain fully functional!"
            ),
            status="unconfigured",
            model=groq_model,
        )

    try:
        from groq import Groq, AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError
    except ImportError:
        logger.error("groq package is not installed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Groq library is not installed on the server",
        )

    # Build conversation messages with bounded history
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Add user context to system knowledge if logged in
    if current_user:
        messages.append(
            {
                "role": "system",
                "content": (
                    f"CURRENT AUTHENTICATED USER CONTEXT:\n"
                    f"- Name: {current_user.name}\n"
                    f"- Email: {current_user.email}\n"
                    f"- Role: {current_user.role}\n"
                    f"- Department: {current_user.department or 'None'}\n"
                    f"- User ID: {current_user.id}"
                ),
            }
        )
    else:
        messages.append(
            {
                "role": "system",
                "content": "GUEST CONTEXT: The user is currently not logged in. If they wish to check their private complaints or submit an official complaint, kindly advise them to log in.",
            }
        )

    # Append bounded conversation history (latest N messages)
    history = payload.conversation_history[-MAX_HISTORY_MESSAGES:]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # Append current user message
    messages.append({"role": "user", "content": user_message})

    try:
        client = Groq(api_key=groq_api_key, timeout=30.0)

        # Agentic loop for tool calls (max 4 turns to prevent runaway calls)
        created_complaint_info = None
        for _ in range(4):
            completion = client.chat.completions.create(
                model=groq_model,
                messages=messages,
                tools=CHATBOT_TOOLS,
                tool_choice="auto",
                temperature=0.4,
                max_tokens=1024,
            )

            choice = completion.choices[0]
            message_obj = choice.message

            # If no tool calls, return assistant text
            if not message_obj.tool_calls:
                return ChatResponse(
                    response=message_obj.content or "How else can I assist you with your telecom service today?",
                    status="success",
                    model=groq_model,
                    complaint_created=created_complaint_info,
                )

            # Process tool calls
            # 1. Append assistant tool_calls message
            tool_calls_serialized = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message_obj.tool_calls
            ]
            messages.append(
                {
                    "role": "assistant",
                    "content": message_obj.content or "",
                    "tool_calls": tool_calls_serialized,
                }
            )

            # 2. Execute each tool and append tool result
            for tc in message_obj.tool_calls:
                func_name = tc.function.name
                try:
                    func_args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    func_args = {}

                result = execute_tool(func_name, func_args, db, current_user)
                if func_name == "submit_confirmed_complaint" and result.get("success"):
                    created_complaint_info = {
                        "id": result.get("complaint_id"),
                        "status": result.get("status"),
                        "department": result.get("department"),
                    }

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "content": json.dumps(result),
                    }
                )

        # Fallback if loop exceeded
        return ChatResponse(
            response="I have retrieved your telecom information. Please let me know if you need any additional troubleshooting or details.",
            status="success",
            model=groq_model,
            complaint_created=created_complaint_info,
        )

    except AuthenticationError:
        logger.warning("Groq authentication failed: invalid API key")
        return ChatResponse(
            response=(
                "Authentication failed with the Groq AI service. "
                "Please verify that your `GROQ_API_KEY` in `backend/.env` is valid and active."
            ),
            status="auth_error",
            model=groq_model,
        )
    except RateLimitError:
        logger.warning("Groq rate limit exceeded")
        return ChatResponse(
            response=(
                "The AI assistant is experiencing high demand and reached Groq's rate limit. "
                "Please wait a few moments and try your request again."
            ),
            status="rate_limit",
            model=groq_model,
        )
    except APITimeoutError:
        logger.warning("Groq API request timed out")
        return ChatResponse(
            response="The AI request timed out. Please check your connection and try again.",
            status="timeout",
            model=groq_model,
        )
    except APIConnectionError:
        logger.warning("Groq API connection error")
        return ChatResponse(
            response=(
                "Unable to connect to the Groq AI service. "
                "Please check internet connectivity or try again shortly."
            ),
            status="network_error",
            model=groq_model,
        )
    except Exception as exc:
        logger.exception("Unexpected error in chatbot processing: %s", exc)
        return ChatResponse(
            response=(
                "An unexpected issue occurred while processing your request with the AI service. "
                "Our team has logged the event. Please try again shortly."
            ),
            status="error",
            model=groq_model,
        )
