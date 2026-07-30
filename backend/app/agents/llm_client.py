import logging
from typing import Type, TypeVar, Optional, Tuple
from dataclasses import dataclass
from typing import Literal
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from app.core.config import get_settings
from app.agents.key_manager import SequentialKeyManager

logger = logging.getLogger(__name__)
T = TypeVar('T', bound=BaseModel)

# Global key managers (persist across calls)
_groq_key_manager: Optional[SequentialKeyManager] = None
_google_key_manager: Optional[SequentialKeyManager] = None


@dataclass
class LLMCallError:
    stage: Literal["groq", "gemini", "no_provider"]
    message: str


def _get_groq_manager() -> SequentialKeyManager:
    """Initialize or return the Groq key manager."""
    global _groq_key_manager
    if _groq_key_manager is None:
        settings = get_settings()
        _groq_key_manager = SequentialKeyManager(settings.GROQ_API_KEYS)
        logger.info(f"Groq key manager initialized with {len(_groq_key_manager.keys)} keys")
    return _groq_key_manager


def _get_google_manager() -> SequentialKeyManager:
    """Initialize or return the Google key manager."""
    global _google_key_manager
    if _google_key_manager is None:
        settings = get_settings()
        _google_key_manager = SequentialKeyManager(settings.GOOGLE_API_KEYS)
        logger.info(f"Google key manager initialized with {len(_google_key_manager.keys)} keys")
    return _google_key_manager


def _get_groq_chat(schema: Type[T], key: str):
    """Build a ChatGroq instance with the given key."""
    settings = get_settings()
    return ChatGroq(
        api_key=key,
        model=settings.GROQ_MODEL or "llama-3.3-70b-versatile",
        temperature=0,
    ).with_structured_output(schema)


def _get_gemini_chat(schema: Type[T], key: str):
    """Build a ChatGoogleGenerativeAI instance with the given key."""
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        api_key=key,
        model=settings.GEMINI_MODEL or "gemini-1.5-flash",
        temperature=0,
    ).with_structured_output(schema)


def run_structured(prompt: str, schema: Type[T]) -> Tuple[Optional[T], Optional[LLMCallError]]:
    settings = get_settings()
    
    # === TRY GROQ KEYS SEQUENTIALLY ===
    groq_manager = _get_groq_manager()
    
    while groq_manager.has_keys and groq_manager.get_current_key():
        current_key = groq_manager.get_current_key()
        key_short = groq_manager.current_key_short
        
        try:
            logger.info(f"Attempting Groq call with key: {key_short} (remaining: {groq_manager.remaining_keys})")
            chat = _get_groq_chat(schema, current_key)
            result = chat.invoke(prompt)
            
            if result is not None:
                logger.info(f"Groq call succeeded with key: {key_short}")
                return result, None
            
        except Exception as e:
            logger.warning(f"Groq key {key_short} failed: {e}")
            groq_manager.mark_current_key_failed()
            logger.info(f"Switched to next Groq key (remaining: {groq_manager.remaining_keys})")
            continue
    
    logger.warning("All Groq keys exhausted. Falling back to Google keys.")
    
    # === TRY GOOGLE KEYS SEQUENTIALLY ===
    google_manager = _get_google_manager()
    
    while google_manager.has_keys and google_manager.get_current_key():
        current_key = google_manager.get_current_key()
        key_short = google_manager.current_key_short
        
        try:
            logger.info(f"Attempting Google call with key: {key_short} (remaining: {google_manager.remaining_keys})")
            chat = _get_gemini_chat(schema, current_key)
            result = chat.invoke(prompt)
            
            if result is not None:
                logger.info(f"Google call succeeded with key: {key_short}")
                return result, None
            
        except Exception as e:
            logger.warning(f"Google key {key_short} failed: {e}")
            google_manager.mark_current_key_failed()
            logger.info(f"Switched to next Google key (remaining: {google_manager.remaining_keys})")
            continue
    
    return None, LLMCallError(
        stage="no_provider",
        message="All Groq and Google API keys exhausted or invalid."
    )


def reset_key_managers() -> None:
    """Reset all key managers to their first key (useful for testing or recovery)."""
    global _groq_key_manager, _google_key_manager
    if _groq_key_manager:
        _groq_key_manager.reset()
        logger.info("Groq key manager reset to first key")
    if _google_key_manager:
        _google_key_manager.reset()
        logger.info("Google key manager reset to first key")