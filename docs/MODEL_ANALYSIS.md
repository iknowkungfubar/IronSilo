# Model Analysis & Recommendations

## VERIFIED TEST RESULTS

### ✅ PERFECT (4/4 Tests Passed)
| Model | Size | Best For |
|-------|------|----------|
| granite-4.0-h-tiny-GGUF | 4B | Tool-calling specialist |
| Llama-3.2-3B-Instruct-GGUF | 2B | Best balance, fastest |
| Devstral-Small-2507-GGUF | 14B | Best coding + tool-calling |
| Qwen3-Coder-30B-A3B-Instruct-GGUF | 30B | Large coding specialist |

### ✅ GOOD (3/4 Tests Passed)
| Model | Size | Best For |
|-------|------|----------|
| LFM2.5-1.2B-Instruct-GGUF | 0.7B | Tiny/fast tasks |
| Phi-4-mini-instruct-GGUF | 3B | Fast coding |
| Bonsai-4B-gguf | 4B | Reliable medium |
| Bonsai-8B-gguf | 8B | Larger reliable |
| Jan-nano-128k-GGUF | 3B | Long context (128k) |
| Qwen3-VL-8B-Instruct-GGUF | 8B | Vision + general |

### ⚠️ INCONSISTENT (2/4 Tests Passed)
| Model | Size | Issue |
|-------|------|-------|
| Gemma-4-E2B-it-GGUF | 2B | Small Gemma, inconsistent |
| Gemma-4-E4B-it-GGUF | 4B | Medium Gemma, inconsistent |
| Qwen3.5-4B-GGUF | 4B | Small vision model |
| Qwen3.5-9B-GGUF | 9B | Larger vision model |
| Qwen3.5-35B-A3B-GGUF | 35B | Very large, slow |
| gpt-oss-20b-mxfp4-GGUF | 20B | Large, not optimized for your system |

### ❌ BAD (0-1/4 Tests Passed)
| Model | Size | Issue |
|-------|------|-------|
| Bonsai-1.7B-gguf | 2B | **HALLUCINATED** - said Seoul is capital of North Korea |
| SmolLM3-3B-GGUF | 3B | Failed code generation |
| Jan-v1-4B-GGUF | 4B | Failed to respond correctly |

### 🔴 HARDWARE LIMIT (Failed to Load)
| Model | Size | Issue |
|-------|------|-------|
| Qwen3-4B-Instruct-2507-GGUF | 4B | VRAM too small |
| GLM-4.7-Flash-GGUF | 8B | VRAM too small |

---

## RECOMMENDATIONS

### 🗑️ DELETE (Bad models, better alternatives)
```
Bonsai-1.7B-gguf     → Hallucinates. Use Bonsai-4B instead.
SmolLM3-3B-GGUF      → Failed tests. Use LFM2.5-1.2B instead (same size, better).
Jan-v1-4B-GGUF       → Failed tests. Use Llama-3.2-3B instead (better).
```

### 🗑️ REMOVE (Hardware too large for your system)
```
Qwen3-4B-Instruct-2507-GGUF  → Won't load on your VRAM
GLM-4.7-Flash-GGUF           → Won't load on your VRAM
```

### 🤔 CONSIDER REMOVING (Inconsistent/Slow)
```
Gemma-4-E2B-it-GGUF     → Smaller version, E4B performs same
Qwen3.5-4B-GGUF        → Qwen3.5-9B is better at same task
gpt-oss-20b-mxfp4-GGUF  → Large (20B), slower, not optimized for your system
Qwen3.5-35B-A3B-GGUF   → Very large (35B), slow on your hardware
```

### ✅ KEEP (Verified Working Well)

**Top Tier - 100% Perfect:**
- `granite-4.0-h-tiny-GGUF` - Best for tool-calling
- `Llama-3.2-3B-Instruct-GGUF` - Best general purpose, fastest
- `Devstral-Small-2507-GGUF` - Best coding model
- `Qwen3-Coder-30B-A3B-Instruct-GGUF` - Best large coding

**Solid Tier - 75% Good:**
- `LFM2.5-1.2B-Instruct-GGUF` - Best tiny model
- `Phi-4-mini-instruct-GGUF` - Fast coding
- `Bonsai-4B-gguf` - Reliable medium
- `Bonsai-8B-gguf` - Reliable larger medium
- `Jan-nano-128k-GGUF` - Best for long context
- `Qwen3-VL-8B-Instruct-GGUF` - Best for vision tasks

---

## SUMMARY

**Your System Can Handle:** ~15 models well
**Delete/Remove:** 7 models (3 bad, 2 hardware, 2 questionable)

**Optimal Model Selection:**
- **Coding**: Devstral-Small or Qwen3-Coder-30B
- **General**: Llama-3.2-3B
- **Tool-calling**: granite-4.0-h-tiny
- **Tiny/Fast**: LFM2.5-1.2B
- **Vision**: Qwen3-VL-8B
- **Long Context**: Jan-nano-128k