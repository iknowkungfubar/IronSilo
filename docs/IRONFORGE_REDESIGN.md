# IronForge Redesign - Technical Specification

## Overview

IronForge redesign adds autonomous agent orchestration with PAI Algorithm integration to IronSilo workspace.

## Architecture

### Phase 1: Foundation (ForgeGod ↔ OpenCode)

```
dev/
├── ironforge_integration.py    # ForgeGod + OpenCode wiring
├── ironforge_skill.json   # Skill definition
```

### Phase 2: Autonomy (PAI Algorithm)

```
dev/
├── pai_algorithm.py    # OBSERVE → PLAN → EXECUTE → VERIFY loop
```

Features:
- Ideal State Criteria (ISC) extraction
- Five Completion Gates
- Wisdom frame generation

### Phase 3: Intelligence (Wisdom Frames)

```
dev/
├── wisdom_frames.py    # Completion gate validators + wisdom extraction
```

Five Completion Gates:
1. **Build Gate** - Code compiles without errors
2. **Test Gate** - All tests pass
3. **Integration Gate** - Components integrate correctly
4. **Security Gate** - No CVEs, security scan passes
5. **Performance Gate** - Meets latency/resource requirements

### Phase 4: Optimization (Resource Management)

```
dev/
├── resource_manager.py    # VRAM management for AMD RX 7900 GRE
```

Safe configurations:
- 1x 8B (Q4_K_M) - ~4800 MB VRAM
- 1x 14B (Q4_K_M) - ~8000 MB VRAM
- 2x 8B (Q4_K_M) - ~9600 MB VRAM

### Unified CLI

```
dev/
├── ironforge_cli.py    # Unified entry point
```

Usage:
```bash
python dev/ironforge_cli.py status           # Show status
python dev/ironforge_cli.py run "task"    # Run task
python dev/ironforge_cli.py loop          # Start autonomous loop
python dev/ironforge_cli.py wisdom         # Show wisdom frames
python dev/ironforge_cli.py resources      # Show resources
```

## Integration

IronForge integrates with:
- **ForgeGod** - Coding harness (if installed)
- **Lemonade** - AMD ROCm LLM backend
- **SochDB** - Ultra-fast memory backend
- **OpenCode** - Agent orchestration

## Status Check

```python
from dev.ironforge_integration import get_integration

integration = get_integration()
print(integration.status())
```

Expected output:
```json
{
  "forgegod": true,
  "lemonade": true,
  "sochdb": true,
  "workspace": "/path/to/IronSilo",
  "ready": true
}
```