# Separate Monitor Process Design

**Date:** 2026-02-21
**Status:** Approved

## Overview

Refactor the monitoring system to run `ollama ps` in a separate process from the interactive Ollama shell, allowing validation of the actual context size after the parameter is set.

## Requirements

1. Monitor should not run in a loop - execute once after parameter testing
2. Interactive shell and monitor must be separate processes
3. Monitor should report both context size and processor/GPU usage
4. Add sanity check to validate actual context size vs. requested context size
5. Remove redundant 0.5s sleep

## Architecture

### Process Structure

```
Main Program
├── OllamaController (pexpect.spawn "ollama run {model}")
│   ├── Interactive chat process (for /set parameter and Hello test)
│   └── Monitor subprocess (subprocess.run "ollama ps")
└── ContextSearcher (orchestrator)
```

### Component Changes

#### OllamaController Changes

1. **Add monitor subprocess instance** (after line 12):
   ```python
   self.monitor_process = None
   ```

2. **New method: `monitor_context()`**:
   - Spawns `subprocess.run(["ollama", "ps"], ...)`
   - Parses output for model name, context size, processor info
   - Returns dictionary: `{"context_size": int, "processor": str}`
   - Waits for completion with timeout
   - Handles subprocess exceptions

3. **Modified `set_context()` method**:
   - Add step 4.5 after "Hello" response handling
   - Call `self.monitor_context()`
   - Validate returned context size matches what was set
   - Update return type: `bool` → `tuple[bool, dict]`

4. **Keep `close()` unchanged**:
   - Ensure monitor subprocess is killed if still running

#### OllamaMonitor Changes

1. **Replace class with function**:
   - Convert `get_processor_usage()` to standalone function
   - Keep parsing logic for `ollama ps` output
   - Return structured data instead of string status

### Data Flow

1. Controller spawns interactive shell
2. Controller sends `/set parameter {size}`
3. Controller waits for response
4. Controller sends "Hello" message
5. Controller waits for response
6. Controller spawns monitor subprocess
7. Monitor runs `ollama ps` and parses output
8. Controller gets monitor results
9. Controller validates context size match
10. Controller reports results to ContextSearcher

## Technical Details

### Monitor Process

- Uses `subprocess.run()` (not pexpect, since no interactive I/O needed)
- Timeout: 30 seconds (same as current)
- Output parsing: Extract model name, context size, processor from columns
- Must handle cases where model isn't found or parsing fails

### Context Size Validation

- Compare returned context size with what was set
- If mismatch: Log warning, continue with current behavior
- If match: Confidence that parameter was set successfully

### Error Handling

- Monitor subprocess failure → Return None for context size
- Parsing failure → Return default/NOT_FOUND for processor
- Timeout on monitor → Skip validation, continue

## Files to Modify

- `ollama_controller.py`: Add monitor subprocess, new method, modify set_context
- `ollama_monitor.py`: Convert class to function
- `context_searcher.py`: Handle new return type from controller

## Success Criteria

- Monitor runs exactly once after parameter testing
- Controller and monitor are separate processes
- Both context size and processor usage are reported
- Validation confirms context size was set correctly
- No redundant sleeps or loops