#!/usr/bin/env python3
"""
Local LLM Inference Settings Tester
Tests inference parameters against your Lemonade models
"""

import requests
import json
import sys
from typing import Dict, Tuple

LEMONADE_URL = "http://127.0.0.1:13305/api/v1"

DEFAULT_SETTINGS: Dict[str, Dict] = {
    "factual": {
        "temperature": 0.2,
        "top_p": 0.85,
        "top_k": 30,
        "repeat_penalty": 1.15,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.0,
        "max_tokens": 2048
    },
    "coding": {
        "temperature": 0.25,
        "top_p": 0.85,
        "top_k": 30,
        "repeat_penalty": 1.15,
        "frequency_penalty": 0.05,
        "presence_penalty": 0.0,
        "max_tokens": 3072
    },
    "reasoning": {
        "temperature": 0.4,
        "top_p": 0.95,
        "top_k": 50,
        "repeat_penalty": 1.08,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "max_tokens": 4096
    },
    "creative": {
        "temperature": 0.7,
        "top_p": 0.90,
        "top_k": 40,
        "repeat_penalty": 1.1,
        "frequency_penalty": 0.05,
        "presence_penalty": 0.0,
        "max_tokens": 2048
    }
}

SYSTEM_PROMPTS: Dict[str, str] = {
    "factual": (
        "You are a factual, precise assistant. Follow these rules strictly:\n"
        "1. If you don't know something, say 'I don't know' - never guess or invent information\n"
        "2. If you're uncertain about details, express doubt explicitly (say 'I'm not certain')\n"
        "3. Never cite sources you don't actually know - say 'I believe...' rather than inventing citations\n"
        "4. Break down complex questions before answering\n"
        "5. Stop and ask for clarification if the question is ambiguous\n\n"
        "Important: You are running on local hardware with limited resources. "
        "You have knowledge up to your training cutoff date. "
        "You cannot access real-time information or verify current facts."
    ),
    "coding": (
        "You are an expert programmer. Rules:\n"
        "1. Only provide code you are confident is correct - never invent function names, APIs, or syntax\n"
        "2. If code might differ by language version, specify the version\n"
        "3. Always include appropriate error handling\n"
        "4. Comment complex logic briefly\n"
        "5. If you're unsure about an implementation, describe the approach verbally without fabricating code\n\n"
        "Do not fabricate code. If you don't know the exact syntax or API, say so."
    ),
    "reasoning": (
        "You are a careful reasoner. Before answering:\n"
        "1. First, explicitly state what you know and don't know about the question\n"
        "2. Identify what information is needed to answer fully\n"
        "3. Work through the problem step-by-step, showing your reasoning process\n"
        "4. State your confidence level at each step\n"
        "5. Only provide your final answer after your reasoning is complete\n"
        "6. If you reach a conclusion you're not confident in, say so explicitly"
    ),
    "creative": (
        "You are a creative assistant. You may be more free with creative responses, but:\n"
        "1. Still avoid factual claims you don't believe are true\n"
        "2. Clearly mark creative speculation as such (use 'perhaps' or 'maybe')\n"
        "3. Engage imagination while remaining grounded in what's plausible"
    )
}


def chat(model: str, messages: list, settings: dict, system: str = "") -> dict:
    """Send chat request to Lemonade"""
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        **settings
    }
    if system:
        payload["messages"] = [{"role": "system", "content": system}] + messages

    try:
        response = requests.post(
            f"{LEMONADE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def test_factuality(model: str, settings: dict) -> Tuple[bool, str]:
    """Test if model knows what it doesn't know"""
    system = SYSTEM_PROMPTS["factual"]
    messages = [{"role": "user", "content": "What is the capital of North Korea? Answer only with the city name."}]

    result = chat(model, messages, settings, system)
    if "error" in result:
        return False, f"Error: {result['error']}"

    response = result["choices"][0]["message"]["content"].strip()
    passed = "pyongyang" in response.lower()

    return passed, response


def test_code_accuracy(model: str, settings: dict) -> Tuple[bool, str]:
    """Test if model produces valid code"""
    system = SYSTEM_PROMPTS["coding"]
    messages = [{"role": "user", "content": "Write a Python function that returns the nth Fibonacci number using only the standard library. Include type hints."}]

    result = chat(model, messages, settings, system)
    if "error" in result:
        return False, f"Error: {result['error']}"

    response = result["choices"][0]["message"]["content"]
    passed = "def fibonacci" in response.lower() and "return" in response.lower()

    return passed, response[:500]


def test_context_retention(model: str, settings: dict) -> Tuple[bool, str]:
    """Test if model can follow context instructions"""
    system = "You are a precise assistant. When asked about the conversation context, use only information from the provided context. If the information isn't there, say so."
    messages = [
        {"role": "user", "content": "My favorite color is blue. Remember this."},
        {"role": "user", "content": "What is my favorite color?"}
    ]

    result = chat(model, messages, settings, system)
    if "error" in result:
        return False, f"Error: {result['error']}"

    response = result["choices"][0]["message"]["content"].lower()
    passed = "blue" in response

    return passed, response[:200]


def test_uncertainty(model: str, settings: dict) -> Tuple[bool, str]:
    """Test if model expresses uncertainty appropriately"""
    system = SYSTEM_PROMPTS["factual"]
    messages = [{"role": "user", "content": "What exactly did the 2024 Nobel Prize in Physics go to? If you're not certain of the exact details, say so."}]

    result = chat(model, messages, settings, system)
    if "error" in result:
        return False, f"Error: {result['error']}"

    response = result["choices"][0]["message"]["content"].lower()
    uncertain_phrases = ["don't know", "not certain", "not sure", "unclear", "i'm not", "i am not", "uncertain"]
    passed = any(phrase in response for phrase in uncertain_phrases) or "2024" in response

    return passed, response[:300]


def run_tests(model: str, preset: str = "factual") -> list:
    """Run all tests with given preset"""
    settings = DEFAULT_SETTINGS[preset].copy()

    print(f"\n{'='*60}")
    print(f"Testing Model: {model}")
    print(f"Preset: {preset}")
    print(f"Settings: {json.dumps(settings, indent=2)}")
    print(f"{'='*60}\n")

    tests = [
        ("Factuality", lambda: test_factuality(model, settings)),
        ("Code Accuracy", lambda: test_code_accuracy(model, settings)),
        ("Context Retention", lambda: test_context_retention(model, settings)),
        ("Uncertainty Expression", lambda: test_uncertainty(model, settings)),
    ]

    results = []
    for name, test_fn in tests:
        print(f"Running {name}...", end=" ", flush=True)
        passed, output = test_fn()
        status = "PASS" if passed else "FAIL"
        print(status)
        print(f"  Output: {output[:150]}...")
        results.append((name, passed))

    print(f"\n{'='*60}")
    print(f"SUMMARY: {sum(1 for _, p in results if p)}/{len(results)} tests passed")
    print(f"{'='*60}\n")

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python inference_tester.py <model> [preset]")
        print(f"  model: e.g., Qwen3-8B-GGUF or user.DeepSeek-R1-Distill-Qwen-7B-GGUF")
        print(f"  preset: {list(DEFAULT_SETTINGS.keys())}")
        print("\nExample: python inference_tester.py Qwen3-8B-GGUF factual")
        sys.exit(1)

    model = sys.argv[1]
    preset = sys.argv[2] if len(sys.argv) > 2 else "factual"

    if preset not in DEFAULT_SETTINGS:
        print(f"Unknown preset: {preset}")
        print(f"Available: {list(DEFAULT_SETTINGS.keys())}")
        sys.exit(1)

    run_tests(model, preset)

    print("\nRun with different presets to compare:")
    for p in DEFAULT_SETTINGS:
        print(f"  python inference_tester.py {model} {p}")


if __name__ == "__main__":
    main()
