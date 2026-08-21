from __future__ import annotations

import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.engine.base import (
    ConversationMessage,
    EngineConfigurationError,
    EngineError,
    ProviderResponseError,
    ProviderUnavailableError,
    GenerationOptions,
)
from app.core.config import get_settings
from app.engine.manager import engine_manager
from app.core.database import ConversationNotFoundError, DatabaseError
from app.core.dependencies import conversation_repository
from app.core.dependencies import get_current_user
from app.core.database import User

router = APIRouter(prefix="/api", tags=["chat"])


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message content cannot be empty.")
        return value


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=100)
    conversation_id: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=4096)
    context_message_limit: int | None = Field(default=None, ge=1, le=100)
    regenerate: bool = False

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty.")
        return value

    @field_validator("conversation_id")
    @classmethod
    def validate_conversation_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return str(UUID(value))
        except ValueError as error:
            raise ValueError("conversation_id must be a valid UUID.") from error

    def conversation_history(self) -> list[ConversationMessage]:
        return [ConversationMessage(role=item.role, content=item.content) for item in self.history]

    def generation_options(self) -> GenerationOptions:
        return GenerationOptions(temperature=self.temperature, max_tokens=self.max_tokens)


class ChatResponse(BaseModel):
    success: bool
    response: str


def _http_error(error: EngineError) -> HTTPException:
    if isinstance(error, EngineConfigurationError):
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, ProviderUnavailableError):
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, ProviderResponseError):
        code = status.HTTP_502_BAD_GATEWAY
    else:
        code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(status_code=code, detail=str(error))


def _database_error(error: DatabaseError) -> HTTPException:
    if isinstance(error, ConversationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Conversation storage is unavailable.",
    )


def _limit_history(history: list[ConversationMessage], limit: int | None = None) -> list[ConversationMessage]:
    return history[-(limit or get_settings().context_message_limit) :]


def _context_for_request(request: ChatRequest, user_id: str) -> tuple[str, list[ConversationMessage]]:
    if request.conversation_id is None:
        if request.regenerate:
            raise ValueError("Regeneration requires a saved conversation.")
        return request.message, _limit_history(request.conversation_history(), request.context_message_limit)

    saved_history = conversation_repository.history(request.conversation_id, user_id)
    if request.regenerate:
        if not saved_history:
            raise ValueError("There is no message to regenerate.")
        if saved_history[-1].role == "assistant":
            if len(saved_history) < 2 or saved_history[-2].role != "user":
                raise ValueError("There is no user message to regenerate.")
            return saved_history[-2].content, _limit_history(saved_history[:-2], request.context_message_limit)
        if saved_history[-1].role == "user":
            return saved_history[-1].content, _limit_history(saved_history[:-1], request.context_message_limit)
        raise ValueError("There is no message to regenerate.")

    conversation_repository.add_message(request.conversation_id, user_id, "user", request.message)
    return request.message, _limit_history(saved_history, request.context_message_limit)


def _replace_or_save_response(request: ChatRequest, user_id: str, response: str) -> None:
    if request.conversation_id is None:
        return
    if request.regenerate:
        detail = conversation_repository.get_conversation(request.conversation_id, user_id)
        if detail.messages and detail.messages[-1].role == "assistant":
            # Only the final assistant response is replaced; user messages and IDs remain intact.
            conversation_repository.delete_message(detail.messages[-1].id, user_id)
    conversation_repository.add_message(request.conversation_id, user_id, "assistant", response)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: User = Depends(get_current_user)) -> ChatResponse:
    try:
        message, history = _context_for_request(request, user.id)
        response = await engine_manager.generate(message, history, request.generation_options())
    except EngineError as error:
        raise _http_error(error) from error
    except DatabaseError as error:
        raise _database_error(error) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    if not response.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI provider returned an empty response.",
        )
    if request.conversation_id is not None:
        try:
            _replace_or_save_response(request, user.id, response)
        except DatabaseError as error:
            raise _database_error(error) from error
    return ChatResponse(success=True, response=response)


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest, user: User = Depends(get_current_user)) -> StreamingResponse:
    try:
        message, history = _context_for_request(request, user.id)
    except DatabaseError as error:
        raise _database_error(error) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    async def events():
        chunks: list[str] = []
        try:
            async for chunk in engine_manager.generate_stream(message, history, request.generation_options()):
                if chunk:
                    chunks.append(chunk)
                    yield f"data: {json.dumps({'delta': chunk})}\n\n"
            response = "".join(chunks).strip()
            if not response:
                raise ProviderResponseError("The AI provider returned an empty response.")
            if request.conversation_id is not None:
                _replace_or_save_response(request, user.id, response)
            yield "data: {\"done\": true}\n\n"
        except EngineError as error:
            yield f"event: error\ndata: {json.dumps({'detail': str(error)})}\n\n"
        except DatabaseError:
            yield "event: error\ndata: {\"detail\": \"Conversation storage is unavailable.\"}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/engine/status")
async def engine_status() -> dict[str, object]:
    return await engine_manager.status()
