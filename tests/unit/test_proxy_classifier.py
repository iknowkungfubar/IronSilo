"""
Unit tests for proxy/classifier.py module.

Tests cover:
- ModelType enum
- ClassificationResult model
- SemanticClassifier functionality
- ModelRouter functionality
"""

import pytest

from proxy.classifier import (
    ClassificationResult,
    ModelType,
    ModelRouter,
    SemanticClassifier,
)


class TestModelType:
    """Test ModelType enum."""
    
    def test_model_types_exist(self):
        """Test that all expected model types exist."""
        assert ModelType.CODE == "code"
        assert ModelType.FAST == "fast"
        assert ModelType.COMPLEX == "complex"
        assert ModelType.DEFAULT == "default"
    
    def test_model_type_str_conversion(self):
        """Test string conversion."""
        assert str(ModelType.CODE) == "ModelType.CODE"
        assert ModelType.CODE.value == "code"


class TestClassificationResult:
    """Test ClassificationResult model."""
    
    def test_result_creation(self):
        """Test creating a classification result."""
        result = ClassificationResult(
            model_type=ModelType.CODE,
            confidence=0.85,
            reasons=["Code pattern detected"],
        )
        
        assert result.model_type == ModelType.CODE
        assert result.confidence == 0.85
        assert len(result.reasons) == 1
    
    def test_confidence_bounds(self):
        """Test confidence validation."""
        # Valid
        ClassificationResult(model_type=ModelType.CODE, confidence=0.0)
        ClassificationResult(model_type=ModelType.CODE, confidence=1.0)
        
        # Invalid
        with pytest.raises(Exception):
            ClassificationResult(model_type=ModelType.CODE, confidence=-0.1)
        
        with pytest.raises(Exception):
            ClassificationResult(model_type=ModelType.CODE, confidence=1.1)


class TestSemanticClassifier:
    """Test SemanticClassifier class."""
    
    def test_classifier_init(self):
        """Test classifier initialization."""
        classifier = SemanticClassifier()
        
        assert classifier.code_threshold == 0.7
        assert classifier.simple_max_words == 25
        assert classifier.complex_min_words == 50
        assert classifier.default_model == ModelType.CODE
    
    def test_classifier_custom_thresholds(self):
        """Test classifier with custom thresholds."""
        classifier = SemanticClassifier(
            code_threshold=0.5,
            simple_max_words=20,
            complex_min_words=100,
            default_model=ModelType.FAST,
        )
        
        assert classifier.code_threshold == 0.5
        assert classifier.simple_max_words == 20
        assert classifier.complex_min_words == 100
        assert classifier.default_model == ModelType.FAST
    
    def test_classify_empty_messages(self):
        """Test classification with empty messages."""
        classifier = SemanticClassifier()
        result = classifier.classify([])
        
        assert result.model_type == classifier.default_model
        assert result.confidence == 1.0
    
    def test_classify_no_user_message(self):
        """Test classification with no user message."""
        classifier = SemanticClassifier()
        result = classifier.classify([
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "Hello!"},
        ])
        
        assert result.model_type == classifier.default_model
    
    def test_classify_simple_query(self):
        """Test classification of a simple query."""
        classifier = SemanticClassifier()
        result = classifier.classify([
            {"role": "user", "content": "What is Python?"},
        ])
        
        # Should be either FAST or DEFAULT
        assert result.model_type in (ModelType.FAST, ModelType.DEFAULT)
        assert len(result.reasons) > 0
    
    def test_classify_code_request(self):
        """Test classification of a code request."""
        classifier = SemanticClassifier()
        result = classifier.classify([
            {"role": "user", "content": "def hello():\n    print('Hello, World!')"},
        ])
        
        # Should be CODE due to 'def' pattern
        assert result.model_type == ModelType.CODE
        assert len(result.reasons) > 0
    
    def test_classify_code_block(self):
        """Test classification with code block."""
        classifier = SemanticClassifier()
        result = classifier.classify([
            {"role": "user", "content": "Here is the code:\n```python\nprint('test')\n```"},
        ])
        
        assert result.model_type == ModelType.CODE
    
    def test_classify_complex_reasoning(self):
        """Test classification of a complex reasoning request."""
        classifier = SemanticClassifier()
        result = classifier.classify([
            {"role": "user", "content": "Please analyze the following complex problem step by step and compare different approaches to optimize the algorithm architecture methodology strategy"},
        ])
        
        # Should be COMPLEX due to indicators
        assert result.model_type == ModelType.COMPLEX
    
    def test_classify_returns_metadata(self):
        """Test that classification returns metadata."""
        classifier = SemanticClassifier()
        result = classifier.classify([
            {"role": "user", "content": "test"},
        ])
        
        assert "code_score" in result.metadata
        assert "simple_score" in result.metadata
        assert "complex_score" in result.metadata
    
    def test_get_last_user_message(self):
        """Test extracting last user message."""
        classifier = SemanticClassifier()
        
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "First user message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Last user message"},
        ]
        
        last_msg = classifier._get_last_user_message(messages)
        assert last_msg == "Last user message"
    
    def test_score_code_request_with_extensions(self):
        """Test code scoring with file extensions."""
        classifier = SemanticClassifier()
        
        score, reasons = classifier._score_code_request(
            "Create a main.py file",
            [],
        )
        
        assert score > 0
        assert any("extension" in r.lower() for r in reasons)
    
    def test_score_simple_query_short(self):
        """Test simple query scoring with short text."""
        classifier = SemanticClassifier()
        
        score, reasons = classifier._score_simple_query("Hi there")
        
        # Should have some score for being short
        assert score > 0


class TestModelRouter:
    """Test ModelRouter class."""
    
    def test_router_init(self):
        """Test router initialization."""
        endpoints = {
            ModelType.CODE: "http://localhost:8001",
            ModelType.FAST: "http://localhost:8002",
        }
        
        router = ModelRouter(endpoints=endpoints)
        
        assert router.endpoints == endpoints
        assert router.fallback_model == ModelType.DEFAULT
    
    def test_router_custom_fallback(self):
        """Test router with custom fallback."""
        endpoints = {
            ModelType.CODE: "http://localhost:8001",
        }
        
        router = ModelRouter(
            endpoints=endpoints,
            fallback_model=ModelType.CODE,
        )
        
        assert router.fallback_model == ModelType.CODE
    
    def test_route_request(self):
        """Test routing a request."""
        endpoints = {
            ModelType.CODE: "http://localhost:8001",
            ModelType.FAST: "http://localhost:8002",
            ModelType.COMPLEX: "http://localhost:8003",
        }
        
        router = ModelRouter(endpoints=endpoints)
        
        # Simple query should route to FAST
        endpoint, result = router.route([
            {"role": "user", "content": "What is 2+2?"},
        ])
        
        assert endpoint in endpoints.values()
        assert isinstance(result, ClassificationResult)
    
    def test_route_code_request(self):
        """Test routing a code request."""
        endpoints = {
            ModelType.CODE: "http://localhost:8001",
            ModelType.FAST: "http://localhost:8002",
        }
        
        router = ModelRouter(endpoints=endpoints)
        
        endpoint, result = router.route([
            {"role": "user", "content": "def test():\n    return True"},
        ])
        
        # Should route to CODE endpoint
        assert endpoint == "http://localhost:8001"
        assert result.model_type == ModelType.CODE
    
    def test_fallback_when_no_endpoint(self):
        """Test fallback when no endpoint for model type."""
        endpoints = {
            ModelType.DEFAULT: "http://localhost:8000",
        }
        
        router = ModelRouter(
            endpoints=endpoints,
            fallback_model=ModelType.DEFAULT,
        )
        
        # Any request should work due to fallback
        endpoint, result = router.route([
            {"role": "user", "content": "test"},
        ])
        
        assert endpoint == "http://localhost:8000"
    
    def test_health_status(self):
        """Test health status updates."""
        endpoints = {
            ModelType.CODE: "http://localhost:8001",
            ModelType.FAST: "http://localhost:8002",
        }
        
        router = ModelRouter(endpoints=endpoints)
        
        # Mark CODE as unhealthy
        router.update_health(ModelType.CODE, False)
        
        status = router.get_status()
        assert status["endpoints"]["code"]["healthy"] is False
        assert status["endpoints"]["fast"]["healthy"] is True
    
    def test_get_status(self):
        """Test getting router status."""
        endpoints = {
            ModelType.CODE: "http://localhost:8001",
        }
        
        router = ModelRouter(
            endpoints=endpoints,
            fallback_model=ModelType.CODE,
        )
        
        status = router.get_status()
        
        assert "endpoints" in status
        assert "fallback_model" in status
        assert status["fallback_model"] == "code"


class TestClassifierEdgeCases:
    """Test edge cases in classifier."""
    
    def test_very_long_simple_query(self):
        """Test that very long text is not classified as simple."""
        classifier = SemanticClassifier()
        
        long_text = " ".join(["word"] * 100)
        result = classifier.classify([
            {"role": "user", "content": long_text},
        ])
        
        # Should not be FAST due to length
        assert result.model_type != ModelType.FAST
    
    def test_mixed_content(self):
        """Test classification of mixed content."""
        classifier = SemanticClassifier()
        
        result = classifier.classify([
            {"role": "user", "content": "Please analyze this code:\n```python\ndef foo(): pass\n```\nand explain it step by step"},
        ])
        
        # Could be CODE or COMPLEX depending on scoring
        assert result.model_type in (ModelType.CODE, ModelType.COMPLEX)
    
    def test_sql_query(self):
        """Test SQL query classification."""
        classifier = SemanticClassifier()
        
        result = classifier.classify([
            {"role": "user", "content": "SELECT * FROM users WHERE id = 1"},
        ])
        
        # Should be CODE due to SQL pattern
        assert result.model_type == ModelType.CODE
    
    def test_question_with_multiple_sentences(self):
        """Test question with multiple sentences."""
        classifier = SemanticClassifier()
        
        result = classifier.classify([
            {"role": "user", "content": "What is Python? Is it good for beginners? Should I learn it?"},
        ])
        
        # Multiple questions should increase complexity
        assert isinstance(result, ClassificationResult)
        assert len(result.reasons) > 0
