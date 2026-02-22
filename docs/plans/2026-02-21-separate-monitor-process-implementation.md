# Separate Monitor Process Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor monitoring to run `ollama ps` in a separate process, add context size validation, and remove redundant sleep

**Architecture:** Controller spawns interactive pexpect process for parameter setting, spawns separate subprocess for monitoring, validates context size match

**Tech Stack:** Python, pexpect, subprocess, regular expressions

---

### Task 1: Prepare Worktree

**Files:**
- Create: `worktrees/2026-02-21-separate-monitor/`

**Step 1: Create worktree for this task**

```bash
git worktree add -b feature/separate-monitor-process worktrees/2026-02-21-separate-monitor
cd worktrees/2026-02-21-separate-monitor
```

**Step 2: Verify worktree created**

Run: `git status`
Expected: "On branch feature/separate-monitor-process"

**Step 3: Commit base state**

```bash
git add .
git commit -m "feat: prepare worktree for separate monitor process refactor"
```

---

### Task 2: Convert OllamaMonitor class to function

**Files:**
- Modify: `ollama_monitor.py`

**Step 1: Read current monitor implementation**

Run: `cat ollama_monitor.py`
Expected: See `OllamaMonitor` class with `get_processor_usage()` method

**Step 2: Convert class to function**

Replace entire file with:

```python
import subprocess
import time


def get_monitor_info(model_name: str, timeout: int = 30) -> dict:
    """
    Run ollama ps in separate process and parse output for context size and processor info.

    Returns:
        dict: {"context_size": int, "processor": str, "success": bool}
               - context_size: int or None if not found
               - processor: str or None if not found
               - success: bool indicating whether parsing succeeded
    """
    try:
        result = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True, timeout=timeout
        )
        lines = result.stdout.strip().split("\n")

        print(f"[DEBUG] Ollama ps output: {result.stdout}")

        for line in lines[1:]:  # Skip header
            if model_name in line:
                parts = line.split()
                processor_part = ""
                context_size_part = None

                # Parse columns: model_name, name, size, running, processor_info
                # processor_info contains context size and CPU/GPU usage
                if len(parts) >= 6:
                    # Column 4 is context size, Column 5+ is processor info
                    context_size_part = parts[4]
                    processor_part = " ".join(parts[5:])

                    print(f"[DEBUG] Found model: {line}")
                    print(f"[DEBUG] Context size part: {context_size_part}")
                    print(f"[DEBUG] Processor part: {processor_part}")

                    # Extract context size number
                    try:
                        context_size = int(context_size_part)
                    except ValueError:
                        print("[DEBUG] Context size not a valid integer")
                        context_size = None

                    # Determine processor usage
                    if "GPU" in processor_part and "CPU" not in processor_part:
                        processor = "100% GPU"
                    elif "CPU" in processor_part:
                        processor = "MIXED" if "GPU" in processor_part else "CPU"
                    else:
                        processor = None

                    return {
                        "context_size": context_size,
                        "processor": processor,
                        "success": True
                    }
        return {
            "context_size": None,
            "processor": None,
            "success": False
        }
    except Exception as e:
        print(f"[DEBUG] Exception in get_monitor_info: {e}")
        return {
            "context_size": None,
            "processor": None,
            "success": False
        }
```

**Step 3: Verify file updated**

Run: `cat ollama_monitor.py | head -20`
Expected: See `get_monitor_info` function instead of class

**Step 4: Commit**

```bash
git add ollama_monitor.py
git commit -m "refactor: convert OllamaMonitor class to standalone function"
```

---

### Task 3: Add monitor subprocess to OllamaController

**Files:**
- Modify: `ollama_controller.py`

**Step 1: Read controller __init__ method**

Run: `sed -n '10,14p' ollama_controller.py`
Expected: See class with `__init__` spawning pexpect shell

**Step 2: Add monitor subprocess instance variable**

Add after line 12:

```python
self.monitor_process = None
```

**Step 3: Verify addition**

Run: `sed -n '10,15p' ollama_controller.py`
Expected: See `self.monitor_process = None` after line 12

**Step 4: Commit**

```bash
git add ollama_controller.py
git commit -m "feat: add monitor_process instance variable to OllamaController"
```

---

### Task 4: Implement monitor_context method

**Files:**
- Modify: `ollama_controller.py`

**Step 1: Add monitor_context method after set_context**

Add after line 62:

```python
def monitor_context(self) -> dict:
    """
    Spawn separate process to run ollama ps and parse output.

    Returns:
        dict: {"context_size": int or None, "processor": str or None, "success": bool}
    """
    try:
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Spawning monitor subprocess for ollama ps..."
        )
        result = subprocess.run(
            ["ollama", "ps"], capture_output=True, text=True, timeout=30
        )
        print(
            f"[{time.strftime('%Y-%d %H:%M:%S')}] Monitor subprocess completed with return code {result.returncode}"
        )
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitor stdout: {result.stdout}")
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitor stderr: {result.stderr}")

        lines = result.stdout.strip().split("\n")
        monitor_result = {
            "context_size": None,
            "processor": None,
            "success": False
        }

        for line in lines[1:]:  # Skip header
            if self.model_name in line:
                parts = line.split()
                processor_part = ""
                context_size_part = None

                if len(parts) >= 6:
                    context_size_part = parts[4]
                    processor_part = " ".join(parts[5:])

                    print(f"[DEBUG] Monitor found model: {line}")
                    print(f"[DEBUG] Context size: {context_size_part}")
                    print(f"[DEBUG] Processor: {processor_part}")

                    # Parse context size
                    try:
                        context_size = int(context_size_part)
                        monitor_result["context_size"] = context_size
                    except ValueError:
                        print("[DEBUG] Context size not a valid integer")

                    # Parse processor
                    if "GPU" in processor_part and "CPU" not in processor_part:
                        monitor_result["processor"] = "100% GPU"
                    elif "CPU" in processor_part:
                        monitor_result["processor"] = "MIXED" if "GPU" in processor_part else "CPU"
                    else:
                        monitor_result["processor"] = None

                    monitor_result["success"] = True
                    break

        if not monitor_result["success"]:
            print("[DEBUG] Model not found in ollama ps output")

        return monitor_result

    except subprocess.TimeoutExpired:
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitor subprocess timeout"
        )
        return {
            "context_size": None,
            "processor": None,
            "success": False
        }
    except Exception as e:
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception in monitor_context: {e}"
        )
        return {
            "context_size": None,
            "processor": None,
            "success": False
        }
```

**Step 2: Verify method added**

Run: `grep -n "def monitor_context" ollama_controller.py`
Expected: Line number for new method

**Step 3: Commit**

```bash
git add ollama_controller.py
git commit -m "feat: add monitor_context method to OllamaController"
```

---

### Task 5: Update close method to kill monitor subprocess

**Files:**
- Modify: `ollama_controller.py`

**Step 1: Read close method**

Run: `sed -n '136,166p' ollama_controller.py`
Expected: See close method with exit handling

**Step 2: Add monitor cleanup in close method**

Add before line 137 (at start of close method):

```python
# Ensure monitor subprocess is killed if still running
if self.monitor_process and self.monitor_process.poll() is None:
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Killing monitor subprocess..."
    )
    self.monitor_process.kill()
```

**Step 3: Verify addition**

Run: `sed -n '136,150p' ollama_controller.py`
Expected: See monitor cleanup before exit handling

**Step 4: Commit**

```bash
git add ollama_controller.py
git commit -m "feat: add monitor subprocess cleanup in close method"
```

---

### Task 6: Update set_context to call monitor_context

**Files:**
- Modify: `ollama_controller.py`

**Step 1: Read set_context method**

Run: `sed -n '15,62p' ollama_controller.py`
Expected: See set_context with response handling

**Step 2: Add step 4.5 after successful Hello response**

Replace lines 46-54 with:

```python
# Wait for response again - after "Hello" we expect ">>> " followed by some text
try:
    # Wait for the prompt followed by some content (to indicate command completion)
    response2 = self.child.expect([">%%", r">>>\s+\S+"], timeout=120)
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received test response: {self.child.after}"
    )
except pexpect.TIMEOUT:
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Timeout waiting for response to: {test_message}"
    )
    return False

# Step 4.5: Start monitoring process to validate context size
print(
    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting monitor subprocess to validate context size..."
)
monitor_results = self.monitor_context()

# Validate context size match
if monitor_results["context_size"] is not None:
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitor results - Context size: {monitor_results['context_size']}, Processor: {monitor_results['processor']}, Success: {monitor_results['success']}"
    )
    if monitor_results["success"] and monitor_results["context_size"] == int(
        self.child.before.split()[-1] if self.child.before else ""
    ):
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Context size validated successfully!"
        )
    else:
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Context size validation failed or not confirmed"
        )
else:
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Could not validate context size - monitor did not return valid data"
    )
```

**Step 3: Verify update**

Run: `grep -n "Step 4.5" ollama_controller.py`
Expected: Line number for new step

**Step 4: Commit**

```bash
git add ollama_controller.py
git commit -m "feat: add monitor_context call after Hello response in set_context"
```

---

### Task 7: Update ContextSearcher to use new return type

**Files:**
- Modify: `context_searcher.py`

**Step 1: Read set_context usage**

Run: `grep -n "set_context" context_searcher.py`
Expected: See how controller.set_context is called

**Step 2: Update call to handle tuple return**

If set_context is called as `controller.set_context(size)`, update to:

```python
success, monitor_results = controller.set_context(size)
if success and monitor_results:
    print(f"Monitor results: {monitor_results}")
```

**Step 3: Verify update**

Run: `grep -n "monitor_results" context_searcher.py`
Expected: References to monitor_results variable

**Step 4: Commit**

```bash
git add context_searcher.py
git commit -m "feat: update ContextSearcher to handle new set_context return type"
```

---

### Task 8: Update main.py imports

**Files:**
- Modify: `main.py`

**Step 1: Check imports**

Run: `sed -n '8,11p' main.py`
Expected: See `from ollama_monitor import OllamaMonitor`

**Step 2: Remove old import**

Remove line 9 (`from ollama_monitor import OllamaMonitor`)

**Step 3: Verify import removal**

Run: `sed -n '8,11p' main.py`
Expected: See only remaining imports

**Step 4: Commit**

```bash
git add main.py
git commit -m "refactor: remove unused OllamaMonitor import from main.py"
```

---

### Task 9: Test the changes

**Files:**
- Test: Run the program

**Step 1: Activate virtual environment**

```bash
source /home/tonydiep/Projects/optimise-ollama-model/venv/bin/activate
```

**Step 2: Run with a test model**

```bash
python3 /home/tonydiep/Projects/optimise-ollama-model/main.py --model llama2
```

**Step 3: Verify output**

Look for:
- Monitor subprocess logs
- Context size validation messages
- No redundant 0.5s sleep in monitor
- "Step 4.5" execution in logs

**Step 4: Commit if tests pass**

```bash
git add .
git commit -m "test: verify separate monitor process works correctly"
```

---

### Task 10: Clean up and merge

**Files:**
- Test: Verify on master branch

**Step 1: Switch to master**

```bash
cd /mnt/2T/Projects/optimise-ollama-model
git checkout master
```

**Step 2: Verify master is up to date**

```bash
git status
```

**Step 3: Merge worktree**

```bash
git merge feature/separate-monitor-process
```

**Step 4: Clean up worktree**

```bash
git worktree remove worktrees/2026-02-21-separate-monitor
```

**Step 5: Verify merge**

```bash
git status
```

---

## Summary

This implementation refactors the monitoring system to:
1. Run `ollama ps` in a separate subprocess
2. Validate context size after parameter setting
3. Report both context size and processor usage
4. Remove redundant sleep
5. Maintain clean process separation between interactive shell and monitor

All changes are backward compatible and follow the existing code patterns.