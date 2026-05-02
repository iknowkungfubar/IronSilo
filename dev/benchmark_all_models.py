#!/usr/bin/env python3
"""
Comprehensive LLM Benchmark for Lemonade Models
Tests all downloaded models with proper load/unload timing
"""

import requests
import json
import time
import sys
from typing import Dict, Tuple, List, Optional

LEMONADE_URL = "http://127.0.0.1:13305/api/v1"
TIMEOUT = 180  # seconds per model for loading + test

MODELS_TO_TEST = [
    # Small/fast models
    ("LFM2.5-1.2B-Instruct-GGUF", "factual", "tiny,fast"),
    ("Bonsai-1.7B-gguf", "factual", "tiny"),
    ("Jan-v1-4B-GGUF", "factual", "small"),
    ("granite-4.0-h-tiny-GGUF", "factual", "tool-calling"),
    ("SmolLM3-3B-GGUF", "factual", "small"),
    ("Gemma-4-E4B-it-GGUF", "factual", "small,gemma"),
    ("Gemma-4-E2B-it-GGUF", "factual", "tiny,gemma"),
    ("Llama-3.2-3B-Instruct-GGUF", "factual", "standard"),
    ("Phi-4-mini-instruct-GGUF", "factual", "fast,coding"),
    ("Jan-nano-128k-GGUF", "factual", "long-context"),

    # Medium models
    ("Bonsai-4B-gguf", "factual", "medium"),
    ("Qwen3-4B-Instruct-2507-GGUF", "factual", "medium"),
    ("Qwen3.5-4B-GGUF", "factual", "medium,vision"),
    ("gpt-oss-20b-mxfp4-GGUF", "factual", "medium,hot"),

    # Larger models (may timeout on your system)
    ("Devstral-Small-2507-GGUF", "coding", "coding,tool-calling"),
    ("GLM-4.7-Flash-GGUF", "factual", "tool-calling"),
    ("Qwen3.5-9B-GGUF", "factual", "medium,vision"),
    ("Bonsai-8B-gguf", "factual", "medium"),
    ("Qwen3-VL-8B-Instruct-GGUF", "factual", "vision,medium"),
    ("Qwen3-Coder-30B-A3B-Instruct-GGUF", "coding", "coding,large"),
    ("Qwen3.5-35B-A3B-GGUF", "factual", "large,vision"),
    ("Qwen3.6-27B-GGUF", "factual", "large"),
    ("DeepSeek-Qwen3-8B-GGUF", "reasoning", "reasoning"),
    ("Nemotron-3-Nano-30B-A3B-GGUF", "factual", "large"),
]

SETTINGS = {
    "factual": {
        "temperature": 0.2,
        "top_p": 0.85,
        "top_k": 30,
        "repeat_penalty": 1.15,
        "max_tokens": 2048
    },
    "coding": {
        "temperature": 0.25,
        "top_p": 0.85,
        "top_k": 30,
        "repeat_penalty": 1.15,
        "max_tokens": 3072
    },
    "reasoning": {
        "temperature": 0.4,
        "top_p": 0.95,
        "top_k": 50,
        "repeat_penalty": 1.08,
        "max_tokens": 4096
    }
}

SYSTEM_PROMPT = (
    "You are a factual, precise assistant. Rules:\n"
    "1. If you don't know, say 'I don't know' - never guess\n"
    "2. If uncertain, express doubt explicitly\n"
    "3. Never invent sources or statistics\n"
    "4. Keep responses concise and accurate"
)

TESTS = [
    ("Factual", "What is the capital of North Korea?"),
    ("Code", "Write a Python fibonacci function with type hints"),
    ("Context", "My favorite color is blue. Remember. What is my favorite color?"),
    ("Uncertainty", "Who won the 2024 Nobel Prize in Physics?"),
]


def check_model_available(model: str) -> bool:
    """Check if model is available via API"""
    try:
        response = requests.get(f"{LEMONADE_URL}/models", timeout=5)
        models = response.json().get("data", [])
        return any(m["id"] == model for m in models)
    except:
        return False


def load_model(model: str) -> bool:
    """Attempt to load model by sending a minimal request"""
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }
        response = requests.post(
            f"{LEMONADE_URL}/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        return response.status_code == 200
    except Exception as e:
        return False


def test_model(model: str, preset: str) -> Tuple[int, int, List[str], str]:
    """Run all tests on a model. Returns (passed, total, details, error)"""
    settings = SETTINGS.get(preset, SETTINGS["factual"]).copy()

    results = []
    details = []

    for test_name, prompt in TESTS:
        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": model,
            "messages": messages,
            **settings
        }

        try:
            response = requests.post(
                f"{LEMONADE_URL}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )

            if response.status_code != 200:
                results.append(False)
                details.append(f"{test_name}: HTTP {response.status_code}")
                continue

            content = response.json()["choices"][0]["message"]["content"].lower()

            if test_name == "Factual":
                passed = "pyongyang" in content
            elif test_name == "Code":
                passed = "def fibonacci" in content.lower() or "fibonacci" in content.lower()
            elif test_name == "Context":
                passed = "blue" in content
            else:  # Uncertainty
                passed = any(word in content for word in ["don't know", "not sure", "uncertain", "i don't", "i'm not"])

            results.append(passed)
            details.append(f"{test_name}: {'PASS' if passed else 'FAIL'} - {content[:50]}...")

        except Exception as e:
            results.append(False)
            details.append(f"{test_name}: ERROR - {str(e)[:50]}")

    passed = sum(results)
    total = len(results)
    return passed, total, details, ""


def get_model_size(model: str) -> str:
    """Estimate model size based on name"""
    size_map = {
        "1.2b": "0.7B", "1.7b": "1B", "2b": "1.2B", "3b": "2B",
        "4b": "2.5B", "7b": "4B", "8b": "5B", "14b": "8B",
        "20b": "12B", "30b": "18B", "32b": "20B", "35b": "20B"
    }
    model_lower = model.lower()
    for key, size in size_map.items():
        if key in model_lower:
            return size
    return "unknown"


def benchmark_model(model: str, preset: str, tags: str) -> Dict:
    """Run benchmark on a single model"""
    print(f"\n{'='*60}")
    print(f"Testing: {model}")
    print(f"Preset: {preset} | Tags: {tags}")
    print(f"{'='*60}")

    # Load model first
    print(f"Loading model...", end=" ", flush=True)
    if not load_model(model):
        print("FAILED TO LOAD")
        return {
            "model": model,
            "passed": 0,
            "total": 4,
            "score": 0,
            "tags": tags,
            "size": get_model_size(model),
            "error": "Failed to load"
        }
    print("LOADED")

    # Run tests
    time.sleep(2)  # Brief pause after load

    passed, total, details, error = test_model(model, preset)
    score = int((passed / total) * 100) if total > 0 else 0

    for detail in details:
        print(f"  {detail}")

    return {
        "model": model,
        "passed": passed,
        "total": total,
        "score": score,
        "tags": tags,
        "size": get_model_size(model),
        "error": error
    }


def main():
    print("="*70)
    print("Lemonade LLM Comprehensive Benchmark")
    print("="*70)
    print(f"API: {LEMONADE_URL}")
    print(f"Models to test: {len(MODELS_TO_TEST)}")

    # Verify server is running
    try:
        response = requests.get(f"{LEMONADE_URL}/models", timeout=5)
        available = [m["id"] for m in response.json().get("data", [])]
        print(f"Available models: {len(available)}")
    except Exception as e:
        print(f"Error: Cannot connect to Lemonade at {LEMONADE_URL}")
        print(f"Details: {e}")
        sys.exit(1)

    results = []
    errors = []

    for model, preset, tags in MODELS_TO_TEST:
        if model not in available:
            print(f"\nSkipping {model} - not in available models")
            continue

        result = benchmark_model(model, preset, tags)
        results.append(result)

        if result["error"]:
            errors.append(result)

        # Save progress after each model
        with open("/tmp/benchmark_progress.json", "w") as f:
            json.dump(results, f, indent=2)

        # Wait between models to let system stabilize
        print("\nWaiting 3s for system stability...")
        time.sleep(3)

    # Print summary
    print("\n" + "="*70)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*70)

    # Sort by score descending
    results.sort(key=lambda x: (-x["score"], x["model"]))

    print(f"\n{'Model':<40} {'Score':<8} {'Size':<8} {'Tags'}")
    print("-"*70)

    for r in results:
        status = "✅" if r["score"] >= 75 else "⚠️" if r["score"] >= 50 else "❌"
        error_str = f" [{r['error']}]" if r["error"] else ""
        print(f"{r['model']:<40} {r['score']:>3}%{'':<5} {r['size']:<8} {r['tags']}{error_str}")

    # Category rankings
    print("\n" + "="*70)
    print("CATEGORY RANKINGS")
    print("="*70)

    categories = {
        "coding": [r for r in results if "coding" in r["tags"] and r["score"] > 0],
        "tiny/fast": [r for r in results if r["size"] in ["0.7B", "1B", "2B"] and r["score"] > 0],
        "general": [r for r in results if r["score"] > 0],
    }

    for cat_name, cat_results in categories.items():
        if not cat_results:
            continue
        print(f"\n{cat_name.upper()}:")
        for r in cat_results[:5]:
            print(f"  {r['model']:<35} {r['score']:>3}% ({r['size']})")

    # Save final results
    output_file = "/home/turin/IronSilo/docs/BENCHMARK_RESULTS.md"
    with open(output_file, "w") as f:
        f.write("# Lemonade Model Benchmark Results\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Total Models Tested:** {len(results)}\n\n")
        f.write(f"**Average Score:** {sum(r['score'] for r in results) // len(results) if results else 0}%\n\n")

        f.write("## All Results\n\n")
        f.write("| Model | Score | Size | Tags |\n")
        f.write("|-------|-------|------|------|\n")
        for r in results:
            f.write(f"| {r['model']} | {r['score']}% | {r['size']} | {r['tags']} |\n")

    print(f"\n\nResults saved to: {output_file}")

    if errors:
        print(f"\n⚠️ {len(errors)} models failed to load:")
        for e in errors:
            print(f"  - {e['model']}: {e['error']}")


if __name__ == "__main__":
    main()
