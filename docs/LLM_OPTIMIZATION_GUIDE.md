# IronSilo — LLM Optimization for RX 7900 GRE 16GB

## Hardware Constraints

| Spec | Value |
|------|-------|
| GPU | AMD Radeon RX 7900 GRE |
| VRAM | **16GB** (not 24GB — critical constraint) |
| Backend | LM Studio Vulkan (llama.cpp vulkan-avx2) |
| ROCm | Installed but LM Studio uses Vulkan |
| Models path | `/run/media/turin/Data/lmstudio/models/` |
| Current best | `qwen3.5-9b-deepseek-v4-flash` (6.9GB, ~6s tool calls) |

## Model Recommendations by VRAM Budget

### Tier 1: 4B-9B Class (Fits comfortably, leaves room for context)

| Model | Size | Quant | VRAM | Notes |
|-------|------|-------|------|-------|
| Qwen3-4B | 4.2B | Q4_K_M | ~4GB | Best 4B class. Strong tool-calling, 32K ctx |
| Qwen3-8B | 8.2B | Q4_K_M | ~7GB | Sweet spot. ~9GB leaves 7GB for 64K ctx |
| Qwen3-Coder-8B | 8.2B | Q4_K_M | ~7GB | Code-focused variant |
| Llama 3.2-8B | 8B | Q4_K_M | ~7GB | Strong general purpose |
| Mistral Small 3.1 | 8B | Q4_K_M | ~7GB | Good instruction following |
| Phi-4-mini | 3.8B | Q4_K_M | ~3.5GB | Microsoft, strong reasoning for size |
| **Qwen3.5-9B-DSV4-Flash** | **9B** | **Q4_K_M** | **~8GB** | **Currently best performer. Keep as default.** |

### Tier 2: 12B-16B Class (Tight fit, limited context)

| Model | Size | Quant | VRAM | Notes |
|-------|------|-------|------|-------|
| Qwen3-14B | 14B | Q3_K_M | ~9GB | Usable with 32K ctx, ~7GB remaining |
| Qwen3-Coder-14B | 14B | Q3_K_M | ~9GB | Code variant, same constraints |
| DeepSeek-V3-Lite | 16B | Q3_K_M | ~10GB | Needs careful ctx management |

### Tier 3: 30B MoE (Specialized use only)

| Model | Size | Quant | VRAM | Notes |
|-------|------|-------|------|-------|
| Qwen3-30B-A3B | 30B MoE (3B active) | Q4_K_M | ~10GB | **Best large model for 16GB VRAM.** Only 3B active params so inference is fast. 16K ctx recommended. |
| DeepSeek-Coder-V2-Lite | 16B MoE | Q4_K_M | ~8GB | 2B active params, very fast |

## Quantization Strategy for 16GB VRAM

```
Q4_K_M — Best balance of quality/speed for 16GB
Q3_K_M — Use for 14B+ models to fit in VRAM  
Q5_K_M — Only for sub-7B models (overkill for larger)
IQ4_XS — 4-bit with ~5% quality loss, saves ~1GB over Q4_K_M
```

**Rule:** If VRAM free after model load < 2GB, reduce context length. If < 1GB, downgrade quantization.

## Harness Techniques to Bridge Small→Frontier

### 1. Speculative Decoding (Highest Impact)
- **How it works:** Small draft model (~1B) predicts tokens, large target model (~9B) verifies in parallel
- **LM Studio:** Built-in speculative decoding via `--draft-model` flag
- **Draft model candidates:** Llama 3.2-1B, Qwen3-0.5B, Phi-3-mini-1B (all fit in <2GB)
- **Speedup:** 1.5-3x for tool-calling tasks
- **VRAM cost:** +1-2GB for draft model
- **IronSilo integration:** Add as LM Studio backend config option

### 2. Headroom Context Compression (Already Integrated)
- **Current:** 47-92% compression, ±0.001 accuracy delta
- **Optimization:** Route long-context queries through Headroom before LLM
- **CacheAligner:** Share compressed representations across agent turns
- **VRAM savings:** ~30% less context memory pressure

### 3. RAG Quality Pipeline
- Small models benefit disproportionately from good RAG
- **Better than fine-tuning** for factual accuracy
- LightRAG graph-based retrieval > simple semantic search
- **Recommendation:** Fix the fake-search bug in `rag/main.py` first

### 4. Prompt Architecture for Small Models
- **Prefix-tuning templates:** Every tool call prepended with structured format examples
- **System prompt compression:** Keep under 2K tokens for 9B models, under 1K for <7B
- **Chain-of-thought:** Use `reasoning_format` parameter (LM Studio) or explicit "think step by step" 
- **Few-shot selection:** Dynamic exemplar retrieval from LightRAG matching current task type
- **Tool-calling format:** Strict JSON schema enforcement via `response_format` (OpenAI-compatible)

### 5. Multi-Turn Consistency
- **Self-consistency:** Run 3-5 inferences, majority-vote the tool call arguments
- **Beam search:** Not practical for real-time agent work (too slow)
- **Reflection:** Have the model review its own output before executing tool calls
- **Cost:** 2-3x latency, but reduces tool-call errors by ~40%

## LM Studio Configuration for IronSilo

```json
{
  "model": "qwen3.5-9b-deepseek-v4-flash",
  "context_length": 64000,
  "gpu_layers": -1,           // Offload all to GPU
  "flash_attention": true,     // Critical for 64K ctx on 16GB
  "cache_type": "q4_0",        // KV cache quantization saves ~40% VRAM
  "threads": 8,                // Match CPU core count
  "batch_size": 512,           // Tokens per batch
  "ubatch_size": 256,          // Micro-batch for GPU
  "speculative": {
    "draft_model": "qwen3-0.5b-q4_k_m",
    "draft_ratio": 0.3
  },
  "reasoning_format": "deepseek-r1",  // For Chain-of-Thought tasks
  "response_format": {
    "type": "json_object"      // For tool-calling tasks
  }
}
```

## GPU Memory Budget Allocation

```
16GB Total VRAM
├── Model weights (Q4_K_M 9B)     → ~8GB
├── KV Cache (64K ctx, Q4)        → ~3GB  
├── Draft model (speculative)      → ~1.5GB
├── Scratch / overhead             → ~1GB
└── Free / headroom                → ~2.5GB
                               Total: ~16GB
```

## IronSilo Integration Roadmap

1. **Fix the wiring issues first** (CDP loop, Caddy prefix strip, fake RAG)
2. **Add model routing** by task type to the proxy layer
3. **Integrate speculative decoding** via LM Studio config
4. **Wire Headroom CacheAligner** for cross-turn context reuse
5. **Fix LightRAG** to return real scores, enable proper RAG for small models
