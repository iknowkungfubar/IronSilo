"""Prompt compression engine using LLMLingua.

Extracted from proxy.py to create an independently testable compression module.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# LLMLingua compressor — lazy-initialized on first use
_compressor: Any = None


def _sanitize_content(content: str) -> str:
    """Sanitize content before compression."""
    return content.replace("\x00", "").strip()


def _compress_content(content: str, compressor: Any = None, enabled: bool = False) -> str:
    """Compress prompt content using LLMLingua or a provided compressor."""
    if not enabled or not content:
        return content

    try:
        comp = compressor or _get_compressor()
        if comp is None:
            return content
        compressed = comp.compress(content, target_token=512)
        result = compressed["compressed_prompt"] if isinstance(compressed, dict) else str(compressed)
        logger.debug("Compressed %d -> %d chars", len(content), len(result))
        return result
    except Exception as e:
        logger.warning("Compression failed: %s — returning uncompressed", e)
        return content


def _get_compressor() -> Any:
    """Lazy-initialize and return the LLMLingua compressor."""
    global _compressor
    if _compressor is not None:
        return _compressor
    try:
        from llmlingua import PromptCompressor
        _compressor = PromptCompressor()
        logger.info("LLMLingua compressor initialized")
    except ImportError:
        logger.warning("LLMLingua not available — compression disabled")
        _compressor = None
    return _compressor


def process_messages(
    messages: list,
    compressor: Any = None,
    compress_enabled: bool = False,
    min_compress_chars: int = 1000,
) -> list[dict[str, str]]:
    """Process a message list, optionally compressing long user messages.

    Accepts both dict messages and Pydantic Message objects.
    """
    processed: list[dict[str, str]] = []
    for msg in messages:
        # Handle both dict and Pydantic Message objects
        if hasattr(msg, "model_dump"):
            msg_dict = msg.model_dump(exclude_none=True)
        elif hasattr(msg, "get"):
            msg_dict = msg
        else:
            msg_dict = {"role": getattr(msg, "role", "user"), "content": str(msg)}

        content = msg_dict.get("content")  # can be None
        role = msg_dict.get("role", "")

        # Convert role enum to string
        if hasattr(role, "value"):
            role = role.value

        if role == "user" and content and len(content) > min_compress_chars:
            sanitized = _sanitize_content(str(content))
            compressed = _compress_content(sanitized, compressor, compress_enabled)
            processed.append({"role": role, "content": compressed})
        elif content is not None:
            processed.append({"role": role, "content": content})
        else:
            processed.append({"role": role})
    return processed
