"""
Pydantic schemas for the Generative AI module.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class GenTask(str, Enum):
    """The supported generation tasks."""

    summary = "summary"
    explain = "explain"
    faq = "faq"
    interview_questions = "interview_questions"
    action_items = "action_items"
    deadlines = "deadlines"


class GenerateRequest(BaseModel):
    """Run a task on either raw text OR a stored document (exactly one)."""

    task: GenTask
    text: str | None = Field(default=None, description="Raw text to process.")
    document_id: int | None = Field(default=None, description="Stored document id.")

    @model_validator(mode="after")
    def _exactly_one_source(self) -> "GenerateRequest":
        if bool(self.text) == bool(self.document_id):
            raise ValueError("Provide exactly one of 'text' or 'document_id'.")
        return self


class FAQItem(BaseModel):
    question: str
    answer: str


class DeadlineItem(BaseModel):
    text: str
    due: str | None = None


class GenerateResponse(BaseModel):
    """Unified response; only the field relevant to the task is populated."""

    task: GenTask
    model_used: str
    source: str = Field(description="'gemini' or 'fallback'.")
    cached: bool

    summary: str | None = None
    explanation: str | None = None
    faq: list[FAQItem] | None = None
    interview_questions: list[str] | None = None
    action_items: list[str] | None = None
    deadlines: list[DeadlineItem] | None = None


class GenAIStatus(BaseModel):
    """Whether live Gemini generation is configured."""

    gemini_enabled: bool
    model: str
