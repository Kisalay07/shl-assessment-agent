from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str  # single letter code: K/P/A/B/C/D/E/S, or combined e.g. "K,S"


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation] = Field(default_factory=list)
    end_of_conversation: bool = False
