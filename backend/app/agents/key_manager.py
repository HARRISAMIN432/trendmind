from typing import List, Optional, Iterator

class SequentialKeyManager:
    
    def __init__(self, keys: List[str]):
        self.keys = keys
        self._current_index = 0
    
    def get_current_key(self) -> Optional[str]:
        """Return the current active key, or None if all keys are exhausted."""
        if self._current_index >= len(self.keys):
            return None
        return self.keys[self._current_index]
    
    def mark_current_key_failed(self) -> None:
        """Move to the next key (current key has failed)."""
        if self._current_index < len(self.keys):
            self._current_index += 1
    
    def reset(self) -> None:
        """Reset to the first key (for testing or recovery)."""
        self._current_index = 0
    
    @property
    def has_keys(self) -> bool:
        return bool(self.keys)
    
    @property
    def remaining_keys(self) -> int:
        return max(0, len(self.keys) - self._current_index)
    
    @property
    def current_key_short(self) -> str:
        """Return masked version of current key for logging."""
        key = self.get_current_key()
        if not key:
            return "None"
        return f"{key[:8]}...{key[-4:]}"