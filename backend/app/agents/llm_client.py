from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


@dataclass
class LLMCallError:
    stage: str  # "groq" | "gemini" | "no_provider"
    message: str


def _get_groq_chat(schema: Type[T]):
    from langchain_groq import ChatGroq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    llm = ChatGroq(model=DEFAULT_GROQ_MODEL, api_key=api_key, temperature=0)
    return llm.with_structured_output(schema)


def _get_gemini_chat(schema: Type[T]):
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    llm = ChatGoogleGenerativeAI(
        model=DEFAULT_GEMINI_MODEL, google_api_key=api_key, temperature=0
    )
    return llm.with_structured_output(schema)


def run_structured(
    prompt: str, schema: Type[T]
) -> tuple[T | None, LLMCallError | None]:
    """
    Calls Groq first; falls back to Gemini on any exception. Returns the
    parsed Pydantic object, or None + an LLMCallError describing what failed.
    """
    groq_chat = None
    try:
        groq_chat = _get_groq_chat(schema)
        if groq_chat is not None:
            result = groq_chat.invoke(prompt)
            return result, None
    except Exception as exc: 
        groq_error = str(exc)
    else:
        groq_error = "GROQ_API_KEY not set"

    try:
        gemini_chat = _get_gemini_chat(schema)
        if gemini_chat is not None:
            result = gemini_chat.invoke(prompt)
            return result, None
        return None, LLMCallError(
            stage="no_provider",
            message=f"Groq failed ({groq_error}) and GOOGLE_API_KEY not set",
        )
    except Exception as exc:  # noqa: BLE001
        return None, LLMCallError(
            stage="gemini", message=f"Groq failed ({groq_error}); Gemini failed ({exc})"
        )