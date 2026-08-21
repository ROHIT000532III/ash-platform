from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

from app.core.database import Conversation, ConversationDetail, ConversationNotFoundError, DatabaseError
from app.core.dependencies import conversation_repository
from app.core.dependencies import get_current_user
from app.core.database import User

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse]


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Conversation title cannot be empty.")
        return value


def _conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(**conversation.__dict__)


def _detail_response(detail: ConversationDetail) -> ConversationDetailResponse:
    return ConversationDetailResponse(
        **detail.conversation.__dict__,
        messages=[MessageResponse(**message.__dict__) for message in detail.messages],
    )


def _database_error(error: DatabaseError) -> HTTPException:
    if isinstance(error, ConversationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Conversation storage is unavailable.")


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(user: User = Depends(get_current_user)) -> ConversationResponse:
    try:
        return _conversation_response(conversation_repository.create_conversation(user.id))
    except DatabaseError as error:
        raise _database_error(error) from error


@router.get("", response_model=list[ConversationResponse])
def list_conversations(user: User = Depends(get_current_user)) -> list[ConversationResponse]:
    try:
        return [_conversation_response(item) for item in conversation_repository.list_conversations(user.id)]
    except DatabaseError as error:
        raise _database_error(error) from error


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: UUID, user: User = Depends(get_current_user)) -> ConversationDetailResponse:
    try:
        return _detail_response(conversation_repository.get_conversation(str(conversation_id), user.id))
    except DatabaseError as error:
        raise _database_error(error) from error


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: UUID, user: User = Depends(get_current_user)) -> Response:
    try:
        conversation_repository.delete_conversation(str(conversation_id), user.id)
    except DatabaseError as error:
        raise _database_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def rename_conversation(
    conversation_id: UUID, request: RenameConversationRequest, user: User = Depends(get_current_user)
) -> ConversationResponse:
    try:
        return _conversation_response(
            conversation_repository.rename_conversation(str(conversation_id), user.id, request.title)
        )
    except DatabaseError as error:
        raise _database_error(error) from error
