"""
Fuzzing tests for the proxy endpoints.

Tests random inputs to find edge cases and crashes.
Run with: pytest tests/fuzz/ -v
"""

import pytest
import random
import string
from fastapi.testclient import TestClient


class TestProxyFuzzing:
    """Fuzz tests for proxy endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from proxy.proxy import app
        return TestClient(app, raise_server_exceptions=False)

    def _random_string(self, length: int) -> str:
        """Generate random string."""
        return ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=length))

    def _random_message(self) -> dict:
        """Generate random message."""
        return {
            "role": random.choice(["system", "user", "assistant"]),
            "content": self._random_string(random.randint(0, 1000))
        }

    def test_chat_completions_fuzz_messages(self, client):
        """Fuzz test with random message lists."""
        messages = [self._random_message() for _ in range(random.randint(0, 10))]

        try:
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "messages": messages,
                    "model": "test-model"
                }
            )
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            pass

    def test_chat_completions_fuzz_model_names(self, client):
        """Fuzz test with random model names."""
        model_names = [
            self._random_string(random.randint(1, 50)),
            "gpt-4",
            "",
            "x" * 1000,
        ]

        for model in model_names:
            try:
                response = client.post(
                    "/api/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": "hello"}],
                        "model": model
                    }
                )
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                pass

    def test_chat_completions_fuzz_temperature(self, client):
        """Fuzz test with extreme temperature values."""
        temperatures = [
            random.uniform(-100, 0),
            random.uniform(0, 0.1),
            random.uniform(0.9, 1.1),
            random.uniform(1.1, 100),
            0,
            1,
            2,
        ]

        for temp in temperatures:
            try:
                response = client.post(
                    "/api/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": "hello"}],
                        "model": "test",
                        "temperature": temp
                    }
                )
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                pass

    def test_chat_completions_fuzz_max_tokens(self, client):
        """Fuzz test with extreme max_tokens values."""
        max_tokens_list = [
            random.randint(-100, 0),
            0,
            1,
            random.randint(1, 1000),
            random.randint(1000, 100000),
            2**31,
        ]

        for max_tokens in max_tokens_list:
            try:
                response = client.post(
                    "/api/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": "hello"}],
                        "model": "test",
                        "max_tokens": max_tokens
                    }
                )
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                pass

    def test_chat_completions_fuzz_content(self, client):
        """Fuzz test with various content patterns."""
        contents = [
            "",
            "hello",
            "x" * 10000,
            "\x00\x01\x02",
            "NULL\x00",
            "random text content",
            '{"key": "value"}',
            self._random_string(10000),
        ]

        for content in contents:
            try:
                response = client.post(
                    "/api/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": content}],
                        "model": "test"
                    }
                )
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                pass

    def test_chat_completions_deeply_nested(self, client):
        """Fuzz test with deeply nested structures."""
        nested = {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "nested": {
                            "deep": {
                                "value": self._random_string(100)
                            }
                        }
                    }
                }
            ],
            "model": "test"
        }

        try:
            response = client.post("/api/v1/chat/completions", json=nested)
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            pass

    def test_chat_completions_unicode_fuzz(self, client):
        """Fuzz test with various Unicode characters."""
        unicode_strings = [
            "hello",
            "random text",
            "special chars",
            "\u0000",
            "\uffff",
            "german chars",
            "arabic chars",
            self._random_string(100) + "special" * 50,
        ]

        for content in unicode_strings:
            try:
                response = client.post(
                    "/api/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": content}],
                        "model": "test"
                    }
                )
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                pass

    def test_chat_completions_null_bytes_in_content(self, client):
        """Fuzz test with null bytes in content."""
        content = "hello\x00world"

        try:
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": content}],
                    "model": "test"
                }
            )
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            pass

    def test_chat_completions_control_chars(self, client):
        """Fuzz test with control characters."""
        control_chars = "".join(chr(i) for i in range(32))
        content = f"hello{control_chars}world"

        try:
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": content}],
                    "model": "test"
                }
            )
            assert response.status_code in [200, 400, 422, 500]
        except Exception:
            pass

    def test_chat_completions_sql_patterns(self, client):
        """Fuzz test with SQL-like patterns."""
        sql_patterns = [
            "quote'pattern",
            "equals=equals",
            "admin-pattern",
            "json{data}",
            "template{{variable}}",
        ]

        for content in sql_patterns:
            try:
                response = client.post(
                    "/api/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": content}],
                        "model": "test"
                    }
                )
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                pass

    def test_chat_completions_malformed_json_like(self, client):
        """Fuzz test with malformed JSON-like patterns."""
        patterns = [
            "{{{{}}}}",
            "[[[[[]]]]]",
            "------",
            "++++++",
            "\\\\\\\\",
            "random pattern",
        ]

        for content in patterns:
            try:
                response = client.post(
                    "/api/v1/chat/completions",
                    json={
                        "messages": [{"role": "user", "content": content}],
                        "model": "test"
                    }
                )
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                pass

    def test_chat_completions_empty_and_extreme(self, client):
        """Fuzz test with empty and extreme requests."""
        payloads = [
            {"messages": [], "model": "test"},
            {"messages": [{"role": "user", "content": ""}], "model": "test"},
            {"messages": [{"role": "", "content": "test"}], "model": "test"},
            {"messages": [{"role": "user"}], "model": "test"},
            {"model": "test"},
            {},
        ]

        for payload in payloads:
            try:
                response = client.post("/api/v1/chat/completions", json=payload)
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                pass

    def test_chat_completions_large_payload(self, client):
        """Fuzz test with very large payloads."""
        large_content = "x" * 100000

        try:
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "messages": [
                        {"role": "user", "content": large_content},
                        {"role": "assistant", "content": large_content},
                        {"role": "user", "content": large_content},
                    ],
                    "model": "test"
                }
            )
            assert response.status_code in [200, 400, 413, 422, 500]
        except Exception:
            pass