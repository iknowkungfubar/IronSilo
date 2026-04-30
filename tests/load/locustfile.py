"""
Locust load test file for the LLMLingua Proxy.

Run with:
    locust -f tests/load/locustfile.py --headless -u 100 -r 10 --run-time 30s --host http://localhost:8080

Or with the web UI:
    locust -f tests/load/locustfile.py --host http://localhost:8080
"""

import random
import time
from typing import List, Optional

from locust import HttpUser, task, between, events


class ChatUser(HttpUser):
    """Simulates a user making chat requests."""

    wait_time = between(0.1, 0.5)
    _request_count = 0

    @task(10)
    def chat_completion(self):
        """Send a chat completion request."""
        self._request_count += 1

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Tell me about task {self._request_count}"},
        ]

        payload = {
            "messages": messages,
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 100,
        }

        start_time = time.time()

        with self.client.post(
            "/api/v1/chat/completions",
            json=payload,
            catch_response=True,
        ) as response:
            elapsed = time.time() - start_time

            if response.status_code == 200:
                response.success()
            elif response.status_code in [502, 503, 504]:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

    @task(5)
    def chat_completion_with_context(self):
        """Send a chat completion with extended context."""
        messages = [
            {"role": "system", "content": "You are a code reviewer."},
            {"role": "user", "content": "Review this code: " + "x = 1\n" * 100},
            {"role": "assistant", "content": "This code has issues..."},
            {"role": "user", "content": "What issues did you find?"},
        ]

        payload = {
            "messages": messages,
            "model": "test-model",
            "temperature": 0.5,
            "max_tokens": 200,
        }

        with self.client.post(
            "/api/v1/chat/completions",
            json=payload,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

    @task(2)
    def streaming_chat(self):
        """Send a streaming chat completion request."""
        payload = {
            "messages": [{"role": "user", "content": "Count to 10"}],
            "model": "test-model",
            "stream": True,
        }

        with self.client.post(
            "/api/v1/chat/completions",
            json=payload,
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

    @task(3)
    def health_check(self):
        """Check the health endpoint."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")


class BurstUser(HttpUser):
    """Simulates burst traffic patterns."""

    wait_time = between(0.01, 0.05)

    @task
    def burst_requests(self):
        """Send rapid burst of requests."""
        for _ in range(10):
            payload = {
                "messages": [{"role": "user", "content": "Quick question"}],
                "model": "test-model",
            }

            self.client.post(
                "/api/v1/chat/completions",
                json=payload,
            )


class ErrorRateUser(HttpUser):
    """Focused on measuring error rates."""

    wait_time = between(0.1, 0.3)

    @task
    def measure_error_rate(self):
        """Measure error rates under normal load."""
        payload = {
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "test-model",
        }

        with self.client.post(
            "/api/v1/chat/completions",
            json=payload,
            catch_response=True,
        ) as response:
            if response.status_code in [200, 502, 503, 504]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


request_times: List[float] = []
error_count = 0
success_count = 0


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track request times and errors."""
    global request_times, error_count, success_count

    if exception:
        error_count += 1
    else:
        request_times.append(response_time)
        success_count += 1


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Print summary stats when tests complete."""
    global request_times, error_count, success_count

    if request_times:
        avg_time = sum(request_times) / len(request_times)
        max_time = max(request_times)
        min_time = min(request_times)

        print(f"\n{'='*60}")
        print(f"Load Test Summary")
        print(f"{'='*60}")
        print(f"Total Requests: {success_count + error_count}")
        print(f"Successful: {success_count}")
        print(f"Failed: {error_count}")
        if success_count + error_count > 0:
            print(f"Error Rate: {error_count / (success_count + error_count) * 100:.2f}%")
        print(f"\nResponse Times (ms):")
        print(f"  Average: {avg_time:.2f}")
        print(f"  Min: {min_time:.2f}")
        print(f"  Max: {max_time:.2f}")
        print(f"{'='*60}\n")
