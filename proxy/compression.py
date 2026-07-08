"""Prompt compression engine using Headroom.

Replaces LLMLingua + torch with Headroom — a CPU-native context
compression library that runs on ONNX runtime. No GPU required.

Headroom features used:
- SmartCrusher: JSON tool output compression (up to 92%)
- CodeCompressor: AST-aware code compression
- General text compression via bundled ONNX model
- CacheAligner: KV-cache prefix optimization
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Headroom compressor — lazy-initialized on first use
_compressor: Any = None


def _sanitize_content(content: str) -> str:
    """Sanitize content before compression. Strips control characters."""
    import re
    content = re.sub(r"[\x00-\x1f\x7f]", "", content)
    return content.strip()


def _get_compressor() -> Any:
    """Lazy-initialize and return the Headroom compressor."""
    global _compressor
    if _compressor is not None:
        return _compressor
    try:
        from headroom import Compressor
        _compressor = Compressor()
        logger.info("Headroom compressor initialized (CPU/ONNX)")
    except ImportError:
        logger.warning("Headroom not available — compression disabled")
        _compressor = None
    except Exception as e:
        logger.warning("Headroom init failed: %s — compression disabled", e)
        _compressor = None
    return _compressor


def _compress_content(content: str, compressor: Any = None, enabled: bool = False) -> str:
    """Compress prompt content using Headroom."""
    if not enabled or not content:
        return content

    try:
        comp = compressor or _get_compressor()
        if comp is None:
            return content

        result = comp.compress(content)
        logger.debug("Compressed %d -> %d chars", len(content), len(result))
        return result
    except Exception as e:
        logger.warning("Compression failed: %s — returning uncompressed", e)
        return content


def _get_role(msg):
    """Get role from a message (dict or object)."""
    return msg.get("role") if isinstance(msg, dict) else msg.role.value if hasattr(msg.role, 'value') else msg.role


def _get_content(msg):
    """Get content from a message (dict or object)."""
    return msg.get("content") if isinstance(msg, dict) else getattr(msg, 'content', "")


def _normalize_msg(msg):
    """Normalize a message to a dict."""
    if isinstance(msg, dict):
        return msg
    return {"role": _get_role(msg), "content": _get_content(msg)}


def process_messages(
    messages: list,
    compressor: Any = None,
    compress_enabled: bool = False,
    bypass: bool = False,
    min_compress_chars: int = 1000,
) -> list:
    """Process a message list, optionally compressing long user messages.

    Args:
        messages: List of message dicts with 'role' and 'content' keys,
                  or objects with .role and .content attributes.
        compressor: Headroom compressor instance (or None for lazy init).
        compress_enabled: Whether compression is active.
        bypass: If True, skip all compression (for vision/dom models).
        min_compress_chars: Minimum content length to trigger compression.

    Returns:
        Processed message list with long messages compressed.
    """
    if bypass or not compress_enabled:
        return [_normalize_msg(msg) for msg in messages]

    processed: list[dict[str, str]] = []
    for msg in messages:
        normalized = _normalize_msg(msg) if not isinstance(msg, dict) else msg
        role = normalized["role"]
        content = normalized.get("content", "")

        if role == "user" and content and len(content) > min_compress_chars:
            sanitized = _sanitize_content(str(content))
            compressed = _compress_content(sanitized, compressor, compress_enabled)
            processed.append({"role": role, "content": compressed})
        else:
            processed.append({"role": role, "content": content})

    return processed
