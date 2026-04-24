"""
Semantic classifier for routing LLM requests.

This module classifies requests to determine the optimal model
for handling different types of tasks (code, simple queries, complex reasoning).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)


class ModelType(str, Enum):
    """Types of models available for routing."""
    
    CODE = "code"           # Code generation/editing (Qwen 2.5 Coder)
    FAST = "fast"           # Simple queries (Llama 3 8B)
    COMPLEX = "complex"     # Complex reasoning (Claude 3.5 Sonnet)
    DEFAULT = "default"     # Default model


class ClassificationResult(BaseModel):
    """Result of semantic classification."""
    
    model_type: ModelType
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticClassifier:
    """
    Classifies LLM requests to determine optimal model routing.
    
    Features:
    - Code detection via regex and heuristics
    - Simple query detection (short, factual)
    - Complex reasoning detection (multi-step analysis)
    - Configurable thresholds
    - Fallback to default model
    """
    
    # Code detection patterns
    CODE_PATTERNS = [
        # Code blocks
        r'```[\s\S]*```',
        # Python functions
        r'def\s+\w+\s*\(',
        # Python classes
        r'class\s+\w+\s*[:\(]',
        # JavaScript/TypeScript functions
        r'function\s+\w+\s*\(',
        # Arrow functions
        r'=>\s*[{(]',
        # Variable declarations with code-like patterns
        r'(?:const|let|var)\s+\w+\s*=\s*(?:function|\(|\[|{|["\']|true|false|null|\d)',
        # Import/require statements
        r'(?:import|require)\s*[\({]',
        # Common programming keywords
        r'\b(?:return|async|await|yield|throw|try|catch)\b',
        # HTML/XML tags
        r'<[a-zA-Z][^>]*>',
        # SQL patterns
        r'\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b',
        # API endpoint patterns
        r'(?:GET|POST|PUT|DELETE|PATCH)\s+["\']?/[\w/]+',
        # JSON-like structures
        r'\{\s*"[^"]+"\s*:',
        # Regex patterns
        r'/(?:[^/\\]|\\.)+/[gimsuy]*',
    ]
    
    # Simple query indicators
    SIMPLE_INDICATORS = [
        # Question words with short queries
        r'^(?:what|who|when|where|why|how|is|are|can|do|does)\s',
        # Direct requests
        r'^(?:tell|give|show|explain)\s',
        # Simple definitions
        r'^(?:define|meaning of|definition of)\s',
    ]
    
    # Complex reasoning indicators
    COMPLEX_INDICATORS = [
        # Multi-step requests
        r'\b(?:step by step|first.*then|after.*before)\b',
        # Analysis requests
        r'\b(?:analyze|compare|contrast|evaluate|assess)\b',
        # Long-form requests
        r'\b(?:essay|report|summary of)\b',
        # Problem-solving
        r'\b(?:solve|fix|debug|troubleshoot|optimize)\b',
        # Multi-part questions
        r'\?[^?]*\?',
        # Lists and enumerations
        r'(?:1\.|•|\*)\s*.*\n(?:2\.|•|\*)',
        # Conditional logic
        r'\b(?:if.*then|unless|provided that|assuming)\b',
    ]
    
    def __init__(
        self,
        code_threshold: float = 0.7,
        simple_max_words: int = 25,
        complex_min_words: int = 50,
        default_model: ModelType = ModelType.CODE,
    ):
        """
        Initialize classifier with thresholds.
        
        Args:
            code_threshold: Minimum score to classify as code
            simple_max_words: Maximum words for simple query
            complex_min_words: Minimum words for complex query
            default_model: Default model type
        """
        self.code_threshold = code_threshold
        self.simple_max_words = simple_max_words
        self.complex_min_words = complex_min_words
        self.default_model = default_model
        
        # Pre-compile patterns for performance
        self._code_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.CODE_PATTERNS]
        self._simple_patterns = [re.compile(p, re.IGNORECASE) for p in self.SIMPLE_INDICATORS]
        self._complex_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.COMPLEX_INDICATORS]
    
    def classify(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """
        Classify a request to determine optimal model.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            context: Optional context for classification
            
        Returns:
            ClassificationResult with model type and confidence
        """
        if not messages:
            return ClassificationResult(
                model_type=self.default_model,
                confidence=1.0,
                reasons=["No messages provided"],
            )
        
        # Get the last user message
        last_message = self._get_last_user_message(messages)
        if not last_message:
            return ClassificationResult(
                model_type=self.default_model,
                confidence=1.0,
                reasons=["No user message found"],
            )
        
        # Calculate scores for each type
        code_score, code_reasons = self._score_code_request(last_message, messages)
        simple_score, simple_reasons = self._score_simple_query(last_message)
        complex_score, complex_reasons = self._score_complex_reasoning(last_message, messages)
        
        # Determine model type
        reasons = []
        
        if code_score >= self.code_threshold:
            return ClassificationResult(
                model_type=ModelType.CODE,
                confidence=code_score,
                reasons=code_reasons,
                metadata={
                    "code_score": code_score,
                    "simple_score": simple_score,
                    "complex_score": complex_score,
                },
            )
        
        if simple_score > complex_score and simple_score > 0.5:
            return ClassificationResult(
                model_type=ModelType.FAST,
                confidence=simple_score,
                reasons=simple_reasons,
                metadata={
                    "code_score": code_score,
                    "simple_score": simple_score,
                    "complex_score": complex_score,
                },
            )
        
        if complex_score > 0.6:
            return ClassificationResult(
                model_type=ModelType.COMPLEX,
                confidence=complex_score,
                reasons=complex_reasons,
                metadata={
                    "code_score": code_score,
                    "simple_score": simple_score,
                    "complex_score": complex_score,
                },
            )
        
        # Default classification
        word_count = len(last_message.split())
        reasons.append(f"Default classification (words: {word_count})")
        
        return ClassificationResult(
            model_type=self.default_model,
            confidence=0.5,
            reasons=reasons,
            metadata={
                "code_score": code_score,
                "simple_score": simple_score,
                "complex_score": complex_score,
                "word_count": word_count,
            },
        )
    
    def _get_last_user_message(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Get the last user message content."""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                return msg.get('content', '')
        return None
    
    def _score_code_request(
        self,
        text: str,
        messages: List[Dict[str, str]],
    ) -> Tuple[float, List[str]]:
        """Score text for code request indicators."""
        reasons = []
        score = 0.0
        matches = 0
        
        # Check code patterns
        for pattern in self._code_patterns:
            if pattern.search(text):
                matches += 1
                if matches <= 3:
                    reasons.append(f"Code pattern detected: {pattern.pattern[:30]}...")
        
        # Score based on matches
        if matches > 0:
            score = min(matches / 3, 1.0)
        
        # Check for code-related context in conversation history
        code_context_count = sum(
            1 for msg in messages[:-1]
            if msg.get('role') == 'assistant' and '```' in msg.get('content', '')
        )
        if code_context_count > 0:
            score = min(score + 0.2, 1.0)
            reasons.append(f"Code context in history: {code_context_count} messages")
        
        # Check for file extensions in text
        file_extensions = re.findall(r'\.\w{2,4}\b', text)
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.rs', '.go', '.rb', '.php'}
        if any(ext in code_extensions for ext in file_extensions):
            score = min(score + 0.3, 1.0)
            reasons.append(f"Code file extension detected: {file_extensions}")
        
        return score, reasons
    
    def _score_simple_query(self, text: str) -> Tuple[float, List[str]]:
        """Score text for simple query indicators."""
        reasons = []
        score = 0.0
        
        word_count = len(text.split())
        
        # Short text bonus
        if word_count <= self.simple_max_words:
            score += 0.3
            reasons.append(f"Short query ({word_count} words)")
        
        # Simple question patterns
        for pattern in self._simple_patterns:
            if pattern.search(text):
                score += 0.4
                reasons.append(f"Simple question pattern: {pattern.pattern[:30]}...")
                break
        
        # Single sentence bonus
        sentence_count = len([s for s in re.split(r'[.!?]+', text) if s.strip()])
        if sentence_count <= 2:
            score += 0.2
            reasons.append(f"Short text ({sentence_count} sentences)")
        
        # No code indicators
        code_matches = sum(1 for p in self._code_patterns if p.search(text))
        if code_matches == 0:
            score += 0.1
            reasons.append("No code patterns detected")
        
        return min(score, 1.0), reasons
    
    def _score_complex_reasoning(
        self,
        text: str,
        messages: List[Dict[str, str]],
    ) -> Tuple[float, List[str]]:
        """Score text for complex reasoning indicators."""
        reasons = []
        score = 0.0
        
        word_count = len(text.split())
        
        # Long text bonus
        if word_count >= self.complex_min_words:
            score += 0.3
            reasons.append(f"Long query ({word_count} words)")
        
        # Complex reasoning patterns
        complex_matches = 0
        for pattern in self._complex_patterns:
            if pattern.search(text):
                complex_matches += 1
                if complex_matches <= 3:
                    reasons.append(f"Complex pattern: {pattern.pattern[:30]}...")
        
        if complex_matches > 0:
            score += min(complex_matches * 0.2, 0.4)
        
        # Multi-paragraph bonus
        paragraphs = [p for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) >= 2:
            score += 0.2
            reasons.append(f"Multi-paragraph ({len(paragraphs)} paragraphs)")
        
        # Technical terms bonus
        technical_terms = re.findall(r'\b(?:algorithm|architecture|framework|implementation|optimization|analysis|methodology|algorithm|strategy|approach)\b', text, re.IGNORECASE)
        if len(technical_terms) >= 2:
            score += 0.2
            reasons.append(f"Technical terms: {technical_terms[:3]}")
        
        # Question marks (multiple questions)
        question_count = text.count('?')
        if question_count >= 2:
            score += 0.1
            reasons.append(f"Multiple questions ({question_count})")
        
        return min(score, 1.0), reasons


class ModelRouter:
    """
    Routes requests to appropriate LLM endpoints based on classification.
    
    Features:
    - Multiple endpoint support
    - Health checking
    - Load balancing (optional)
    - Fallback mechanism
    """
    
    def __init__(
        self,
        endpoints: Dict[ModelType, str],
        classifier: Optional[SemanticClassifier] = None,
        fallback_model: ModelType = ModelType.DEFAULT,
        health_check_interval: int = 60,
    ):
        """
        Initialize router with endpoints.
        
        Args:
            endpoints: Mapping of ModelType to endpoint URL
            classifier: Semantic classifier instance
            fallback_model: Fallback model type
            health_check_interval: Seconds between health checks
        """
        self.endpoints = endpoints
        self.classifier = classifier or SemanticClassifier()
        self.fallback_model = fallback_model
        self.health_check_interval = health_check_interval
        
        # Health status
        self._health_status: Dict[ModelType, bool] = {model: True for model in endpoints}
        
        logger.info(
            "Model router initialized",
            endpoints={m.value: url for m, url in endpoints.items()},
            fallback=fallback_model.value,
        )
    
    def route(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, ClassificationResult]:
        """
        Route request to appropriate endpoint.
        
        Args:
            messages: Chat messages
            context: Optional routing context
            
        Returns:
            Tuple of (endpoint_url, classification_result)
        """
        # Classify request
        result = self.classifier.classify(messages, context)
        model_type = result.model_type
        
        logger.debug(
            "Request classified",
            model_type=model_type.value,
            confidence=result.confidence,
            reasons=result.reasons[:3],
        )
        
        # Get endpoint for model type
        endpoint = self._get_endpoint(model_type)
        
        if endpoint:
            return endpoint, result
        
        # Fallback to default
        logger.warning(
            f"No endpoint for {model_type.value}, using fallback",
            fallback=self.fallback_model.value,
        )
        
        fallback_endpoint = self._get_endpoint(self.fallback_model)
        if fallback_endpoint:
            return fallback_endpoint, result
        
        # Last resort - use first available endpoint
        for model, url in self.endpoints.items():
            if self._health_status.get(model, True):
                logger.warning(f"Using first available endpoint: {model.value}")
                return url, result
        
        raise RuntimeError("No healthy endpoints available")
    
    def _get_endpoint(self, model_type: ModelType) -> Optional[str]:
        """Get endpoint URL for model type."""
        endpoint = self.endpoints.get(model_type)
        
        if endpoint and self._health_status.get(model_type, True):
            return endpoint
        
        return None
    
    def update_health(self, model_type: ModelType, is_healthy: bool) -> None:
        """Update health status for a model."""
        old_status = self._health_status.get(model_type, True)
        self._health_status[model_type] = is_healthy
        
        if old_status != is_healthy:
            logger.info(
                f"Health status changed",
                model=model_type.value,
                healthy=is_healthy,
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Get router status."""
        return {
            "endpoints": {
                model.value: {
                    "url": url,
                    "healthy": self._health_status.get(model, False),
                }
                for model, url in self.endpoints.items()
            },
            "fallback_model": self.fallback_model.value,
        }
