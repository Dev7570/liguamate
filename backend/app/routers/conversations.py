"""Conversations Router - The core chat API with SSE streaming support"""

import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.chat import SendMessageRequest, MessageResponse, ConversationCreate, ConversationResponse
from app.services.chat_service import (
    create_conversation,
    process_message,
    process_message_stream,
    end_conversation,
    delete_conversation,
    get_conversation_messages,
    get_user_conversations,
)
from app.services.ai_service import transcribe_audio
from app.utils.auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    request: ConversationCreate = ConversationCreate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new conversation session with Mira."""
    conversation = await create_conversation(db, current_user.id, request.channel)
    return ConversationResponse(
        id=str(conversation.id),
        channel=conversation.channel,
        started_at=str(conversation.started_at),
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and get Mira's response (non-streaming).

    This is THE core endpoint — triggers the full pipeline:
    memory search → prompt assembly → LLM call → signal extraction → storage
    """
    try:
        result = await process_message(
            db=db,
            conversation_id=conversation_id,
            user=current_user,
            user_message=request.content,
        )
        return MessageResponse(
            id=result["id"],
            role=result["role"],
            content=result["content"],
            corrections=[
                {"original": c["original"], "corrected": c["corrected"], "explanation": c.get("explanation")}
                for c in (result.get("corrections") or [])
            ] if result.get("corrections") else None,
            vocab_used=result.get("vocab_used"),
            mood_signal=result.get("mood_signal"),
            created_at=result["created_at"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.post("/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and stream Mira's response via Server-Sent Events (SSE).

    SSE Events:
      data: {"type": "token", "content": "..."}       — live text token
      data: {"type": "done", "message_id": "...", ...} — final metadata with corrections, vocab, mood
    """

    async def event_generator():
        try:
            async for event in process_message_stream(
                db=db,
                conversation_id=conversation_id,
                user=current_user,
                user_message=request.content,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            error_event = {"type": "error", "content": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/transcribe")
async def transcribe_audio_endpoint(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Transcribe an audio file to text using Whisper (Groq or OpenAI).

    Accepts audio files (webm, mp3, wav, m4a, ogg).
    Returns the transcribed text.
    """
    # Validate file type (strip mime parameters like codecs=opus)
    content_type = audio.content_type.split(";")[0].strip().lower() if audio.content_type else ""
    allowed_types = {"audio/webm", "audio/mp3", "audio/mpeg", "audio/wav", "audio/ogg", "audio/m4a", "audio/mp4", "application/octet-stream"}
    if content_type and content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {audio.content_type}. Use webm, mp3, wav, m4a, or ogg.",
        )

    try:
        file_bytes = await audio.read()
        if len(file_bytes) > 25 * 1024 * 1024:  # 25MB limit
            raise HTTPException(status_code=400, detail="Audio file too large. Max 25MB.")

        text = await transcribe_audio(file_bytes, audio.filename or "audio.webm")
        return {"text": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )


@router.post("/{conversation_id}/end", response_model=ConversationResponse)
async def end_conversation_endpoint(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End a conversation session and generate a summary."""
    conversation = await end_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationResponse(
        id=str(conversation.id),
        channel=conversation.channel,
        started_at=str(conversation.started_at),
        ended_at=str(conversation.ended_at),
        summary=conversation.summary,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_endpoint(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    success = await delete_conversation(db, conversation_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found or unauthorized")
    return None


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a conversation."""
    messages = await get_conversation_messages(db, conversation_id, current_user.id)
    return [
        MessageResponse(
            id=str(m.id),
            role=m.role,
            content=m.content,
            corrections=[
                {"original": c["original"], "corrected": c["corrected"], "explanation": c.get("explanation")}
                for c in (m.corrections or [])
            ] if m.corrections else None,
            vocab_used=m.vocab_used,
            mood_signal=m.mood_signal,
            created_at=str(m.created_at),
        )
        for m in messages
    ]


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all conversations for the current user."""
    conversations = await get_user_conversations(db, current_user.id)
    return [
        ConversationResponse(
            id=c["id"],
            channel=c["channel"],
            started_at=c["started_at"],
            ended_at=c.get("ended_at"),
            summary=c.get("summary"),
            message_count=c.get("message_count", 0),
        )
        for c in conversations
    ]
