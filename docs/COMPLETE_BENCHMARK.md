# COMPLETE Model Benchmark Results

**Date:** 2026-05-02
**Total LLMs Tested:** 14 (+ 2 failed to load)
**Tests:** Factual accuracy, Code generation, Context retention, Uncertainty expression

---

## ✅ EXCELLENT (4/4 - 100%)

| Model | Size | Best For |
|-------|------|----------|
| Llama-3.2-3B-Instruct-GGUF | 2B | General purpose, fastest |
| Phi-4-mini-instruct-GGUF | 3B | Coding specialist, fast |
| Qwen3-Coder-30B-A3B-Instruct-GGUF | 30B | Large coding specialist |

---

## ✅ GOOD (3/4 - 75%)

| Model | Size | Best For |
|-------|------|----------|
| granite-4.0-h-tiny-GGUF | 4B | Tool-calling specialist |
| Devstral-Small-2507-GGUF | 14B | Coding + tool-calling |
| LFM2.5-1.2B-Instruct-GGUF | 0.7B | Tiny/fast tasks |
| Bonsai-4B-gguf | 4B | Medium reliable |
| Bonsai-8B-gguf | 8B | Larger medium |
| Jan-nano-128k-GGUF | 3B | Long context (128k) |
| Qwen3-VL-8B-Instruct-GGUF | 8B | Vision tasks |
| Nemotron-3-Nano-30B-A3B-GGUF | 30B | Large general |

---

## 🔴 POOR (0-1/4 - 0-25%)

| Model | Size | Issue |
|-------|------|-------|
| DeepSeek-Qwen3-8B-GGUF | 8B | **Failed to respond correctly** |
| Qwen3.5-9B-GGUF | 9B | **Failed to respond correctly** |
| Gemma-4-E4B-it-GGUF | 4B | **Only 1/4 passed** |

---

## 🔴 FAILED TO LOAD (Hardware Limit)

| Model | Size | Issue |
|-------|------|-------|
| Qwen3-4B-Instruct-2507-GGUF | 4B | VRAM insufficient |
| GLM-4.7-Flash-GGUF | 8B | VRAM insufficient |
| Gemma-4-26B-A4B-it-GGUF | 26B | VRAM insufficient |
| Gemma-4-31B-it-GGUF | 31B | VRAM insufficient |

---

## Audio/Image Models (Not Fully Tested)

| Model | Type | Status |
|-------|------|--------|
| Whisper-Base | Audio transcription | Available |
| Whisper-Large-v3-Turbo | Audio transcription | Available |
| Whisper-Tiny | Audio transcription | Available |
| Flux-2-Klein-4B | Image generation | Available |
| Flux-2-Klein-9B | Image generation | Available |
| SD-Turbo | Image generation | Available |
| SDXL-Turbo | Image generation | Available |
| kokoro-v1 | TTS | Available |
| Qwen3-Embedding-4B-GGUF | Embeddings | Not for chat |

---

## RECOMMENDATIONS

### 🗑️ DELETE (Bad performance - better alternatives)
```
DeepSeek-Qwen3-8B-GGUF   → Nemotron or Qwen3-Coder-30B better
Qwen3.5-9B-GGUF          → Qwen3-VL-8B better for vision
Gemma-4-E4B-it-GGUF      → Only 1/4, Llama-3.2-3B is better
```

### ✅ KEEP (Verified Working)

**Tier 1 - Perfect:**
- `Llama-3.2-3B-Instruct-GGUF` - Best general, fastest
- `Phi-4-mini-instruct-GGUF` - Best coding, fast
- `Qwen3-Coder-30B-A3B-Instruct-GGUF` - Best large coding

**Tier 2 - Excellent 75%:**
- `granite-4.0-h-tiny-GGUF` - Tool-calling
- `Devstral-Small-2507-GGUF` - Coding/tool-calling
- `LFM2.5-1.2B-Instruct-GGUF` - Tiny/fast
- `Bonsai-4B-gguf` - Medium reliable
- `Bonsai-8B-gguf` - Larger medium
- `Jan-nano-128k-GGUF` - Long context
- `Qwen3-VL-8B-Instruct-GGUF` - Vision
- `Nemotron-3-Nano-30B-A3B-GGUF` - Large general

**Remove from consideration:**
- `Qwen3-Embedding-4B-GGUF` - Embeddings only, not for chat
- Large Gemma/Qwen models - Won't load on your hardware

---

## OPTIMAL MODEL SELECTION

| Use Case | Model | Score |
|----------|-------|-------|
| **General chat** | Llama-3.2-3B | 100% |
| **Coding** | Phi-4-mini or Qwen3-Coder-30B | 100% |
| **Tool-calling** | granite-4.0-h-tiny | 75% |
| **Vision** | Qwen3-VL-8B | 75% |
| **Long context** | Jan-nano-128k | 75% |
| **Tiny/fast** | LFM2.5-1.2B | 75% |

**Minimum recommended set:** 4 models (Llama, Phi-4-mini, granite, LFM2.5)
**Extended recommended set:** 8 models (add Bonsai, Jan-nano, Qwen-VL, Nemotron)