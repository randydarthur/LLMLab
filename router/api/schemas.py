"""
Pydantic models for OpenAI-compatible request and response schemas.

These schemas define the structure of incoming chat completion requests
and outgoing responses for both streaming and non-streaming modes.
"""

from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field


# ------------------------------------------------------------
# Message Schema
# ------------------------------------------------------------

class ChatMessage(BaseModel):
    """
    Represents a single chat message in the conversation history.
    Exported.
    """
    role: Literal["user", "assistant", "system"]
    content: str


# ------------------------------------------------------------
# Request Schema
# ------------------------------------------------------------

class ChatCompletionRequest(BaseModel):
    """
    Schema for /v1/chat/completions request.
    Exported.
    """
    model: Optional[str] = None
    messages: List[ChatMessage]
    stream: bool = False
    session_id: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


# ------------------------------------------------------------
# Response Schemas (Non-Streaming)
# ------------------------------------------------------------

class ChatCompletionChoice(BaseModel):
    """
    Represents a single choice in the completion response.
    Exported.
    """
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class UsageInfo(BaseModel):
    """
    Token usage information.
    Exported.
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """
    Schema for non-streaming chat completion response.
    Exported.
    """
    id: str
    object: Literal["chat.completion"]
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[UsageInfo] = None


# ------------------------------------------------------------
# Internal Helpers (Not Exported)
# ------------------------------------------------------------

def build_response(
    model: str,
    messages: List[ChatMessage],
    completion_text: str,
    request_id: str,
) -> ChatCompletionResponse:
    """
    Helper to construct a ChatCompletionResponse from raw text.
    Internal only.
    """
    return ChatCompletionResponse(
        id=request_id,
        object="chat.completion",
        model=model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content=completion_text),
                finish_reason="stop",
            )
        ],
        usage=None,
    )

