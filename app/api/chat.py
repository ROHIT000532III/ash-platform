from fastapi import APIRouter
from pydantic import BaseModel

from app.engine.manager import engine_manager


router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/api/chat")
async def chat(request: ChatRequest):

    response = await engine_manager.generate(request.message)

    return {
        "success": True,
        "response": response,
    }