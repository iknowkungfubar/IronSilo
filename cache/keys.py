"""Cache key builder for LLM requests.

Provides utilities to build deterministic cache keys
from chat messages and request parameters.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


class CacheKeyBuilder:
    """Builds cache keys for LLM requests."""

    @staticmethod
    def build_messages_key(
        messages: List[Dict[str, str]],
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Build cache key from messages.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Temperature setting
            max_tokens: Max tokens setting

        Returns:
            Cache key string
        """
        # Normalize messages
        normalized = []
        for msg in messages:
            normalized.append(
                {
                    "role": msg.get("role", ""),
                    "content": msg.get("content", ""),
                }
            )

        # Create key components
        key_data = {
            "messages": normalized,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Hash the key
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()


__all__ = [
    "CacheKeyBuilder",
]
