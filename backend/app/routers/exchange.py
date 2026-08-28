"""Social Language Exchange Router — WebSocket real-time chat with AI fallback"""

import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user, verify_token
from app.services.ai_service import get_ai_client_and_model, clean_ai_reply

router = APIRouter(prefix="/exchange", tags=["Language Exchange"])

# ─── In-Memory Matching Pool ─────────────────────────────────────────────────
# {user_id: {"user": User, "language": str, "joined_at": datetime, "session_id": str|None}}
_waiting_pool: dict[str, dict] = {}
# {session_id: {"users": [user_id1, user_id2], "connections": {user_id: WebSocket}, "is_ai": bool}}
_active_sessions: dict[str, dict] = {}

# AI partner names pool
_AI_PARTNERS = [
    {"name": "Alex 🤖", "level": "advanced", "bio": "AI conversation partner"},
    {"name": "Suki 🤖", "level": "intermediate", "bio": "AI language buddy"},
    {"name": "Kai 🤖", "level": "advanced", "bio": "AI practice partner"},
]

AI_EXCHANGE_PROMPT = """You are {partner_name}, a friendly language exchange partner chatting with {user_name}.
You are both practicing {language} together through casual conversation.

## Rules
- Chat naturally like a real person, NOT like a teacher or AI assistant
- Keep messages SHORT (1-3 sentences max, like real texting)
- Ask follow-up questions to keep the conversation flowing
- Share your own (made-up) experiences and opinions to feel real
- If the user makes grammar mistakes, gently model the correct form naturally in your reply
- Match the user's energy and vibe
- Use emoji occasionally but not excessively
- Respond in {language} mixed with encouragement
- Level: {user_level} — adjust your vocabulary complexity accordingly
- NEVER say you are an AI. You are {partner_name}, a fellow language learner.
- Start conversations with casual topics: hobbies, travel, food, movies, weekend plans

## Conversation so far:
{history}"""

# Timeout before AI fallback (seconds)
AI_FALLBACK_TIMEOUT = 10


def _get_language_flag(language: str) -> str:
    flags = {
        "English": "🇬🇧", "Spanish": "🇪🇸", "French": "🇫🇷", "German": "🇩🇪",
        "Italian": "🇮🇹", "Japanese": "🇯🇵", "Mandarin": "🇨🇳", "Portuguese": "🇧🇷",
        "Russian": "🇷🇺", "Arabic": "🇸🇦", "Hindi": "🇮🇳", "Korean": "🇰🇷",
        "Dutch": "🇳🇱", "Swedish": "🇸🇪", "Turkish": "🇹🇷",
    }
    return flags.get(language, "🌐")


def _pick_ai_partner():
    import random
    return random.choice(_AI_PARTNERS).copy()


def _create_ai_session(user_id: str, language: str, user_name: str, english_level: str):
    """Create an AI-powered exchange session."""
    session_id = str(uuid.uuid4())
    ai_partner = _pick_ai_partner()

    _active_sessions[session_id] = {
        "users": [user_id, "ai_partner"],
        "connections": {},
        "language": language,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "is_ai": True,
        "ai_partner": ai_partner,
        "ai_history": [],
        "user_name": user_name,
        "user_level": english_level,
    }

    _waiting_pool[user_id] = {
        "session_id": session_id,
        "language": language,
        "user_name": user_name,
        "english_level": english_level,
    }

    return session_id, ai_partner


@router.post("/join")
async def join_pool(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add the current user to the language exchange matching pool."""
    user_language = getattr(current_user, "target_language", "English")

    # Check if already matched
    if current_user.id in _waiting_pool and _waiting_pool[current_user.id].get("session_id"):
        session_id = _waiting_pool[current_user.id]["session_id"]
        session = _active_sessions.get(session_id, {})
        if session.get("is_ai"):
            return {
                "status": "matched",
                "session_id": session_id,
                "is_ai": True,
                "partner": {
                    "name": session["ai_partner"]["name"],
                    "level": session["ai_partner"]["level"],
                    "flag": _get_language_flag(user_language),
                },
            }
        return {
            "status": "matched",
            "session_id": session_id
        }

    # Look for a human partner learning the same language
    partner_id = None
    for uid, info in list(_waiting_pool.items()):
        if uid != current_user.id and info.get("language") == user_language and info.get("session_id") is None:
            partner_id = uid
            break

    if partner_id:
        # Create a human session
        session_id = str(uuid.uuid4())
        _active_sessions[session_id] = {
            "users": [current_user.id, partner_id],
            "connections": {},
            "language": user_language,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "is_ai": False,
        }
        _waiting_pool[current_user.id] = {"session_id": session_id, "language": user_language, "user_name": current_user.name, "english_level": current_user.english_level}
        _waiting_pool[partner_id]["session_id"] = session_id
        return {"status": "matched", "session_id": session_id}
    else:
        # Add to waiting pool — will be matched with AI after timeout on frontend
        _waiting_pool[current_user.id] = {
            "session_id": None,
            "language": user_language,
            "user_name": current_user.name,
            "english_level": current_user.english_level,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"status": "waiting", "language": user_language, "flag": _get_language_flag(user_language)}


@router.post("/join/ai")
async def join_ai_partner(
    current_user: User = Depends(get_current_user),
):
    """Skip waiting and immediately match with an AI partner."""
    user_language = getattr(current_user, "target_language", "English")

    # Clean up any existing waiting pool entry
    old_info = _waiting_pool.get(current_user.id)
    if old_info and old_info.get("session_id"):
        _active_sessions.pop(old_info["session_id"], None)
    _waiting_pool.pop(current_user.id, None)

    session_id, ai_partner = _create_ai_session(
        current_user.id, user_language, current_user.name, current_user.english_level
    )

    return {
        "status": "matched",
        "session_id": session_id,
        "is_ai": True,
        "partner": {
            "name": ai_partner["name"],
            "level": ai_partner["level"],
            "flag": _get_language_flag(user_language),
        },
    }


@router.get("/status")
async def get_status(current_user: User = Depends(get_current_user)):
    """Check current matching status."""
    info = _waiting_pool.get(current_user.id)
    if not info:
        return {"status": "not_in_pool"}
    if info.get("session_id"):
        session_id = info["session_id"]
        session = _active_sessions.get(session_id, {})

        if session.get("is_ai"):
            return {
                "status": "matched",
                "session_id": session_id,
                "is_ai": True,
                "language": session.get("language", "English"),
                "flag": _get_language_flag(session.get("language", "English")),
                "partner": {
                    "name": session["ai_partner"]["name"],
                    "level": session["ai_partner"]["level"],
                    "flag": _get_language_flag(session.get("language", "English")),
                },
            }

        # Human partner
        partner_id = next((uid for uid in session.get("users", []) if uid != current_user.id), None)
        partner_info = _waiting_pool.get(partner_id, {}) if partner_id else {}
        return {
            "status": "matched",
            "session_id": session_id,
            "language": session.get("language", "English"),
            "flag": _get_language_flag(session.get("language", "English")),
            "partner": {
                "name": partner_info.get("user_name", "Partner"),
                "level": partner_info.get("english_level", "beginner"),
                "flag": _get_language_flag(session.get("language", "English")),
            }
        }
    return {"status": "waiting", "language": info.get("language", "English")}


@router.delete("/leave")
async def leave_pool(current_user: User = Depends(get_current_user)):
    """Leave the matching pool or end a session."""
    info = _waiting_pool.pop(current_user.id, None)
    if info and info.get("session_id"):
        session_id = info["session_id"]
        _active_sessions.pop(session_id, None)
    return {"ok": True}


async def _generate_ai_exchange_reply(session: dict, user_message: str) -> str:
    """Generate an AI response for the exchange chat."""
    client, model = get_ai_client_and_model()

    history = session.get("ai_history", [])
    history_text = "\n".join(
        f"{'You' if m['role'] == 'assistant' else session['user_name']}: {m['content']}"
        for m in history[-10:]
    ) or "(Conversation just started — greet them casually!)"

    system_prompt = AI_EXCHANGE_PROMPT.format(
        partner_name=session["ai_partner"]["name"].replace(" 🤖", ""),
        user_name=session["user_name"],
        language=session["language"],
        user_level=session.get("user_level", "beginner"),
        history=history_text,
    )

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.85,
            max_tokens=200,
        )
        reply = clean_ai_reply(response.choices[0].message.content or "")
        return reply or "That's interesting! Tell me more 😊"
    except Exception as e:
        return "Haha nice! What else have you been up to? 😊"


@router.websocket("/chat/{session_id}")
async def exchange_chat(websocket: WebSocket, session_id: str, token: str):
    """Real-time WebSocket chat for a matched exchange session (human or AI)."""
    # Verify token
    user_id = verify_token(token)
    if not user_id:
        await websocket.close(code=4001)
        return

    session = _active_sessions.get(session_id)
    if not session or user_id not in session["users"]:
        await websocket.close(code=4004)
        return

    await websocket.accept()
    session["connections"][user_id] = websocket

    is_ai_session = session.get("is_ai", False)

    if is_ai_session:
        # Send AI partner greeting after a short delay
        partner_name = session["ai_partner"]["name"]
        await websocket.send_json({
            "type": "partner_connected",
            "partner_name": partner_name,
        })
        # Send an AI greeting
        await asyncio.sleep(1.5)
        greeting = await _generate_ai_exchange_reply(session, "(User just connected. Send a casual greeting to start the conversation.)")
        session.setdefault("ai_history", []).append({"role": "assistant", "content": greeting})
        await websocket.send_json({
            "type": "message",
            "content": greeting,
            "sender_id": "ai_partner",
            "sender_name": partner_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    else:
        # Notify human partner that user connected
        user_info = _waiting_pool.get(user_id, {})
        for uid, ws in session["connections"].items():
            if uid != user_id:
                try:
                    await ws.send_json({"type": "partner_connected", "partner_name": user_info.get("user_name", "Partner")})
                except Exception:
                    pass

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            if msg_type == "message":
                content = data.get("content", "")

                if is_ai_session:
                    # Store user message in history
                    session.setdefault("ai_history", []).append({"role": "user", "content": content})

                    # Show typing indicator
                    await websocket.send_json({"type": "typing", "is_typing": True})

                    # Generate AI reply with slight delay for realism
                    await asyncio.sleep(0.8)
                    ai_reply = await _generate_ai_exchange_reply(session, content)
                    session["ai_history"].append({"role": "assistant", "content": ai_reply})

                    await websocket.send_json({"type": "typing", "is_typing": False})
                    await websocket.send_json({
                        "type": "message",
                        "content": ai_reply,
                        "sender_id": "ai_partner",
                        "sender_name": session["ai_partner"]["name"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    # Broadcast to human partner
                    user_info = _waiting_pool.get(user_id, {})
                    payload = {
                        "type": "message",
                        "content": content,
                        "sender_id": user_id,
                        "sender_name": user_info.get("user_name", "Partner"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    for uid, ws in session["connections"].items():
                        if uid != user_id:
                            try:
                                await ws.send_json(payload)
                            except Exception:
                                pass

            elif msg_type == "typing":
                if not is_ai_session:
                    for uid, ws in session["connections"].items():
                        if uid != user_id:
                            try:
                                await ws.send_json({"type": "typing", "is_typing": data.get("is_typing", False)})
                            except Exception:
                                pass

    except WebSocketDisconnect:
        session["connections"].pop(user_id, None)
        if not is_ai_session:
            # Notify human partner
            for uid, ws in session["connections"].items():
                try:
                    await ws.send_json({"type": "partner_left"})
                except Exception:
                    pass
        # Cleanup
        _waiting_pool.pop(user_id, None)
        if not session["connections"]:
            _active_sessions.pop(session_id, None)
