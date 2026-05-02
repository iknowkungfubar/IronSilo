# Local LLM Optimization Guide for Lemonade

## Problem Summary
- Hallucinations (confident false information)
- Stopping abruptly mid-response
- Losing context / confusion in long conversations
- Smaller quantized models (GGUF) don't match frontier model coherence

## Solution Framework: 4 Layers

### Layer 1: Inference Parameters (easiest wins)

**For Factual/Coding Tasks (low hallucination tolerance):**
```json
{
  "temperature": 0.2,
  "top_p": 0.85,
  "top_k": 30,
  "repeat_penalty": 1.15,
  "frequency_penalty": 0.1,
  "presence_penalty": 0.0
}
```

**For Creative/Brainstorming:**
```json
{
  "temperature": 0.7,
  "top_p": 0.90,
  "top_k": 40,
  "repeat_penalty": 1.1,
  "frequency_penalty": 0.05,
  "presence_penalty": 0.0
}
```

**For Reasoning/Chain-of-Thought:**
```json
{
  "temperature": 0.4,
  "top_p": 0.95,
  "top_k": 50,
  "repeat_penalty": 1.08,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0
}
```

**Key Principles:**
- Lower temperature = less fabrication, more deterministic
- Repeat_penalty > 1.0 prevents repetitive loops
- Top_k + top_p together control sampling diversity
- For quantized models: keep temp below 0.5 for factual tasks

---

### Layer 2: System Prompt Engineering

**Effective System Prompt Template:**
```
You are a factual, precise assistant. Follow these rules:
1. If you don't know something, say "I don't know" - never guess
2. If you're uncertain about details, express doubt explicitly
3. Cite sources when you recall them (e.g., "According to...")
4. Break down complex questions before answering
5. Stop and ask for clarification if the question is ambiguous

Context about you:
- You are running on local hardware with limitations
- You have knowledge up to [YOUR_TRAINING_CUTOFF]
- You cannot access real-time information or verify current facts
```

**For Code Generation (specialized):**
```
You are an expert programmer. Rules:
1. Only provide code you are confident is correct
2. If code might differ by language version, specify the version
3. Never invent function names or APIs - only use known ones
4. Include error handling even if not explicitly requested
5. If you're unsure about an implementation, describe the approach verbally without fabricated code

Available context: [RELEVANT CODEBASE]
```

**For Reasoning Tasks:**
```
Before answering:
1. First, explicitly state what you know and don't know
2. Identify what information is needed to answer fully
3. Work through the problem step-by-step (show your reasoning)
4. State your confidence level at each step
5. Only provide final answer after reasoning is complete
```

---

### Layer 3: Context Management

**The 3 Core Problems with Context:**

1. **Context Overflow**: Model truncates or loses early conversation
2. **Attention Drift**: Model loses focus on original query
3. **Knowledge Cutoff Confusion**: Model doesn't know what's recent vs old

**Practical Solutions:**

**A. Explicit Context Boundaries**
```
[SYSTEM: Current date: 2026. You have knowledge up to 2024.]
[SYSTEM: The user is asking about X, which is Y topic...]
[USER: ...new question...]

Always re-state context at conversation start:
"Based on our discussion about X, you're asking about Y..."
```

**B. Information Freshness Flags**
Include timestamps or explicit markers:
```
[INFO: This data is from 2023. Current info may differ.]
[RECENT: This is breaking news from the past week]
[USER_PROVIDED: The user has provided this context directly]
```

**C. Structured Input Formatting**
```
Context Block (use this exact format):
---
Topic: [what this is about]
Date: [when info is from]
Relevance: [why this matters to the question]
---

Question: [specific question]
Format needed: [what output format you want]
Confidence required: [high/medium]
```

**D. Chunk Large Inputs**
For documents/code > 2000 tokens:
- Split into logical sections
- Process one chunk at a time
- Summarize each chunk before moving to next
- Keep running summary of key facts

---

### Layer 4: Architectural Improvements

**For Lemonade/Similar Local Servers:**

1. **Model Selection by Task:**
   | Task | Recommended Model Size |
   |------|------------------------|
   | Code generation | Qwen2.5-Coder-32B or smaller |
   | Simple Q&A | Phi-4-mini, Qwen3-4B |
   | Complex reasoning | DeepSeek-R1-14B (has built-in reasoning) |
   | Long document summarization | Gemma-4-26B (larger context) |

2. **Context Length Management:**
   - Don't max out context - leave 20% buffer
   - For long convos: implement sliding summary window
   - Periodically summarize and compress conversation

3. **Hardware Considerations:**
   - If crashing: reduce batch size, lower context length
   - Q4_K_M quantization: good balance of quality/size
   - More VRAM = larger context window possible

---

## Quick Reference: Model-Specific Settings

### Qwen Models (Qwen2.5, Qwen3)
```json
{
  "temperature": 0.3,
  "top_p": 0.85,
  "repeat_penalty": 1.1,
  "max_tokens": 4096
}
```
- Qwen has strong code能力 but tends to be verbose
- Use explicit length limits to prevent rambling

### DeepSeek (Coder V2, R1)
```json
{
  "temperature": 0.2,
  "top_p": 0.8,
  "repeat_penalty": 1.15
}
```
- R1 models: already trained with reasoning, less CoT needed
- Coder V2: excellent for code, use lower temp for accuracy

### Gemma Models
```json
{
  "temperature": 0.25,
  "top_p": 0.9,
  "repeat_penalty": 1.1
}
```
- Gemma tends to be more factual at lower temps
- Good vision capabilities for image inputs

### Llama Models
```json
{
  "temperature": 0.3,
  "top_p": 0.9,
  "repeat_penalty": 1.12
}
```
- Llama can be repetitive, higher repeat penalty helps
- 3.1 8B: good for simple tasks, don't expect frontier quality

---

## Anti-Hallucination Checklist

Before accepting an LLM response, verify:

- [ ] Does it claim knowledge it shouldn't have?
- [ ] Are there specific details that could be verified?
- [ ] Is it inventing references, dates, or statistics?
- [ ] Does the logic chain make sense step by step?
- [ ] Is it staying on topic or drifting?

**If it Hallucinates:**
1. Ask it to verify specific claims
2. Request sources or reasoning chain
3. Give it explicit "I don't know" permission
4. Try breaking the question into smaller parts

---

## Implementation in IronSilo

Add to `config.yaml` for default inference settings:

```yaml
inference:
  defaults:
    temperature: 0.3
    top_p: 0.85
    repeat_penalty: 1.12
    max_tokens: 4096

  task_overrides:
    coding:
      temperature: 0.25
      repeat_penalty: 1.15
    reasoning:
      temperature: 0.4
      top_p: 0.95
    creative:
      temperature: 0.7
      repeat_penalty: 1.08
```

---

## Testing Your Configuration

```bash
# Test 1: Factuality
echo "What is the capital of Burkina Faso? Answer only if certain." | openaiCompatible \
  --model lemonade/Qwen3-8B-GGUF \
  --temp 0.2

# Expected: "The capital of Burkina Faso is Ouagadougou."
# Hallucination: invents different capital or shows uncertainty

# Test 2: Code accuracy
echo "Write a function that returns the nth Fibonacci number. Only use standard library." | ...

# Test 3: Context retention
# Have a 20-message conversation, then ask something from message #3
```

---

## Summary: Best Practices

| Problem | Solution |
|---------|----------|
| Hallucinations | Lower temp (0.2-0.3), factual system prompt, "I don't know" permission |
| Stopping abruptly | Increase max_tokens, check repeat_penalty |
| Losing context | Explicit context flags, shorter conversations, summarize periodically |
| Confusion | Structured input format, break complex questions |
| Model specific issues | Use right model for task, quantized models need lower temp |

**Remember:** Quantized local models will never fully match frontier models. The goal is to maximize reliability within your hardware constraints. Start with the inference parameter defaults above, then tune based on these principles.
