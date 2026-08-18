"""Social Language Exchange Router — WebSocket real-time human-to-human practice"""

import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user, verify_token

router = APIRouter(prefix="/exchange", tags=["Language Exchange"])

# ─── In-Memory Matching Pool ─────────────────────────────────────────────────
# {user_id: {"user": User, "language": str, "joined_at": datetime, "session_id": str|None}}
_waiting_pool: dict[str, dict] = {}
# {session_id: {"users": [user_id1, user_id2], "connections": {user_id: WebSocket}}}
_active_sessions: dict[str, dict] = {}


def _get_language_flag(language: str) -> str:
    flags = {
        "English": "🇬🇧", "Spanish": "🇪🇸", "French": "🇫🇷", "German": "🇩🇪",
        "Italian": "🇮🇹", "Japanese": "🇯🇵", "Mandarin": "🇨🇳", "Portuguese": "🇧🇷",
        "Russian": "🇷🇺", "Arabic": "🇸🇦", "Hindi": "🇮🇳", "Korean": "🇰🇷",
        "Dutch": "🇳🇱", "Swedish": "🇸🇪", "Turkish": "🇹🇷",
    }
    return flags.get(language, "🌐")


@router.post("/join")
async def join_pool(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add the current user to the language exchange matching pool."""
    user_language = getattr(current_user, "target_language", "English")

    # Check if already matched
    if current_user.id in _waiting_pool and _waiting_pool[current_user.id].get("session_id"):
        return {
            "status": "matched",
            "session_id": _waiting_pool[current_user.id]["session_id"]
        }

    # Look for a partner learning the same language
    partner_id = None
    for uid, info in list(_waiting_pool.items()):
        if uid != current_user.id and info.get("language") == user_language and info.get("session_id") is None:
            partner_id = uid
            break

    if partner_id:
        # Create a session
        session_id = str(uuid.uuid4())
        _active_sessions[session_id] = {
            "users": [current_user.id, partner_id],
            "connections": {},
            "language": user_language,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        # Mark both users as matched
        _waiting_pool[current_user.id] = {"session_id": session_id, "language": user_language, "user_name": current_user.name, "english_level": current_user.english_level}
        _waiting_pool[partner_id]["session_id"] = session_id
        return {"status": "matched", "session_id": session_id}
    else:
        # Add to waiting pool
        _waiting_pool[current_user.id] = {
            "session_id": None,
            "language": user_language,
            "user_name": current_user.name,
            "english_level": current_user.english_level,
        }
        return {"status": "waiting", "language": user_language, "flag": _get_language_flag(user_language)}


@router.get("/status")
async def get_status(current_user: User = Depends(get_current_user)):
    """Check current matching status."""
    info = _waiting_pool.get(current_user.id)
    if not info:
        return {"status": "not_in_pool"}
    if info.get("session_id"):
        session_id = info["session_id"]
        session = _active_sessions.get(session_id, {})
        # Get partner info
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


@router.websocket("/chat/{session_id}")
async def exchange_chat(websocket: WebSocket, session_id: str, token: str):
    """Real-time WebSocket chat for a matched exchange session."""
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

    # Notify partner that user connected
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
                # Broadcast to partner
                payload = {
                    "type": "message",
                    "content": data.get("content", ""),
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
                for uid, ws in session["connections"].items():
                    if uid != user_id:
                        try:
                            await ws.send_json({"type": "typing", "is_typing": data.get("is_typing", False)})
                        except Exception:
                            pass

    except WebSocketDisconnect:
        session["connections"].pop(user_id, None)
        # Notify partner
        for uid, ws in session["connections"].items():
            try:
                await ws.send_json({"type": "partner_left"})
            except Exception:
                pass
        # Cleanup
        _waiting_pool.pop(user_id, None)
        if not session["connections"]:
            _active_sessions.pop(session_id, None)
