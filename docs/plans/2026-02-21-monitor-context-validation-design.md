# Monitor Context Validation Design

**Date:** 2026-02-21
**Status:** Approved

## Overview

Refactor the monitoring system to validate context size setting after the "Hello" test response. The monitor will run in a separate process after parameter validation, extracting both context size and processor usage from `ollama ps` output.

## Requirements

1. **Separate Processes**: The interactive shell (for `/set parameter`) and monitor (`ollama ps`) must run in separate processes
2. **One-Time Monitoring**: Monitor runs once after "Hello" response, not in a loop
3. **Context Size Validation**: Verify the actual context size matches what was set
4. **Processor Usage**: Continue reporting CPU/GPU usage from `ollama ps`
5. **No Redundant Sleep**: Remove the 0.5s sleep since we wait for "Hello" response

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

#### OllamaController

**Changes:**
1. Add `self.monitor_process = None` instance variable
2. Add new method `monitor_context()` to spawn and parse monitor subprocess
3. Modify `set_context()` return type: `bool` → `tuple[bool, dict]`
4. Add validation step after "Hello" response
5. Update `close()` to kill monitor process

**New Method: `monitor_context()`**

```python
def monitor_context(self) -> Optional[dict]:
    """Run ollama ps in separate process and parse results"""
    try:
        result = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            text=True,
            timeout=30
        )
        # Parse output for context size and processor info
        return {
            "context_size": int_value,
            "processor": processor_str
        }
    except Exception as e:
        print(f"[DEBUG] Monitor failed: {e}")
        return None
```

**Modified `set_context()` Method**

After line 54 (after successful "Hello" response):
```python
# Step 4.5: Validate context with monitor
monitor_results = self.monitor_context()
if monitor_results:
    context_size_match = (monitor_results["context_size"] == size)
    print(f"[DEBUG] Context size match: {context_size_match}")
    print(f"[DEBUG] Expected: {size}, Actual: {monitor_results['context_size']}")
    print(f"[DEBUG] Processor: {monitor_results['processor']}")

return (success, monitor_results) if monitor_results else (success, None)
```

**Updated `close()` Method**

After line 165:
```python
# Kill monitor process if still running
if self.monitor_process and self.monitor_process.poll() is None:
    self.monitor_process.terminate()
    try:
        self.monitor_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        self.monitor_process.kill()
```

#### OllamaMonitor

**Changes:**
1. Convert entire class to standalone function
2. Keep parsing logic for `ollama ps` output
3. Return structured data instead of string status

**New Function: `monitor_context()`**

```python
def monitor_context(model_name: str) -> Optional[dict]:
    """Run ollama ps and parse context size and processor usage"""
    try:
        result = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            text=True,
            timeout=30
        )
        lines = result.stdout.strip().split("\n")

        for line in lines[1:]:
            if model_name in line:
                parts = line.split()
                # Parse context size and processor info
                # TODO: Extract actual column positions from ollama ps output
                return {
                    "context_size": extract_context_size(parts),
                    "processor": extract_processor(parts)
                }
        return None
    except Exception as e:
        print(f"[DEBUG] Monitor failed: {e}")
        return None
```

## Data Flow

```
1. Controller spawns interactive shell (pexpect)
2. Controller sends /set parameter {size}
3. Controller waits for prompt response
4. Controller sends "Hello" message
5. Controller waits for response
6. Controller spawns monitor subprocess (subprocess.run)
7. Monitor runs "ollama ps" and parses output
8. Controller receives monitor results
9. Controller validates context size match
10. Controller reports results to ContextSearcher
```

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
- Use debug print statements for visibility

### Error Handling

- Monitor subprocess failure → Return None for context size
- Parsing failure → Return default/NOT_FOUND for processor
- Timeout on monitor → Skip validation, continue
- Model not found in ps output → Return None

## Success Criteria

1. Monitor runs only once after "Hello" response
2. Context size from monitor matches what was set
3. Processor usage reported correctly
4. No redundant 0.5s sleep
5. Separate processes for interactive and monitor
6. Clean process cleanup in `close()`
7. Errors handled gracefully