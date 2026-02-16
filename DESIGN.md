# Technical Design: Ollama Context Optimizer

## 1. Overview

This document describes the technical design for the Ollama Context Optimizer. The application is a command-line tool designed to automatically find the optimal context size (`num_ctx`) for a given Ollama Large Language Model (LLM) to ensure it runs entirely on the GPU.

## 2. Architecture

The application will be built in Python and will consist of three main components that manage the optimization process. It will interact with the system's shell to control and monitor the Ollama processes.

**Components:**

*   **`OllamaController`**: Manages the interactive `ollama run` session. It is responsible for starting the model, sending commands to set the context size, and ultimately saving the optimized model.
*   **`OllamaMonitor`**: Manages the `ollama ps` command. It is responsible for polling the status of the Ollama process and parsing the output to determine the current resource utilization (CPU vs. GPU).
*   **`ContextSearcher`**: Implements the core binary search logic. It uses the `OllamaController` to set context sizes and the `OllamaMonitor` to check the results, adjusting the search range until an optimal size is found.

## 3. Component Breakdown

### 3.1. `ollama_controller.py`

This module will use Python's `subprocess` or a more robust library like `pexpect` to handle the interactive shell. `pexpect` is recommended as it is designed for this type of interaction.

**Class: `OllamaController`**

*   `__init__(self, model_name: str)`
    *   Spawns a new process: `ollama run [model_name]`.
    *   Stores the model name for later use (e.g., for the `/save` command).
    *   Waits for the initial `>>>` prompt to ensure the model is ready.

*   `set_context(self, size: int) -> bool`
    *   Sends the command `/set parameter num_ctx [size]
` to the process.
    *   Sends a follow-up prompt like `Hello
` to ensure the context change is applied.
    *   Reads the output to confirm the command was executed. It should wait until it sees the next `>>>` prompt.
    *   Returns `True` if successful, `False` otherwise.

*   `save_model(self) -> bool`
    *   Sends the command `/save [model_name]
` to the process.
    *   Waids for the confirmation message (`Created new model...`).
    *   Returns `True` on success.

*   `close(self)`
    *   Sends the `/exit` command or terminates the subprocess gracefully.

### 3.2. `ollama_monitor.py`

This module will execute shell commands and parse the string output.

**Class: `OllamaMonitor`**

*   `get_processor_usage(self, model_name: str) -> str`
    *   Executes the command `ollama ps`.
    *   Parses the output to find the line corresponding to `model_name`.
    *   Extracts the value from the "PROCESSOR" column.
    *   **Return Values:** Should be a normalized string, e.g., `"100% GPU"`, `"CPU"`, `"MIXED"`, `"NOT_FOUND"`.
    *   This function needs to be robust and handle cases where the model is not listed or the output is unexpected.

### 3.3. `context_searcher.py`

This module contains the core application logic.

**Class: `ContextSearcher`**

*   `__init__(self, controller: OllamaController, monitor: OllamaMonitor)`
    *   Initializes with instances of the controller and monitor.

*   `find_optimal_size(self, min_size: int, max_size: int) -> int`
    *   Implements the binary search algorithm within the `[min_size, max_size]` range.
    *   `low = min_size`, `high = max_size`, `last_good_size = min_size`.
    *   **Loop:**
        1.  `mid = (low + high) // 2`
        2.  Call `self.controller.set_context(mid)`.
        3.  Wait a brief moment for the change to apply, then call `self.monitor.get_processor_usage()`. This might require a retry loop for stability.
        4.  **Decision Logic:**
            *   If usage is `"100% GPU"`: This size is good. Store it (`last_good_size = mid`) and try a larger size (`low = mid + 1`).
            *   If usage is `"CPU"` or `"MIXED"`: This size is too large. Try a smaller size (`high = mid - 1`).
        5.  **Termination Condition:**
            *   The loop terminates when `low > high`.
            *   **Early Exit:** If at any point `(high - low) < 1000` and the last check was `"100% GPU"`, the search can terminate early, returning `last_good_size`.
    *   Returns `last_good_size`.

### 3.4. `main.py`

This is the entry point of the application.

*   Uses `argparse` to handle command-line arguments: `--model`, `--min`, `--max`.
*   Initializes `OllamaController` and `OllamaMonitor`.
*   Initializes `ContextSearcher`.
*   Calls `find_optimal_size` to start the search.
*   Once an optimal size is found, it calls `controller.save_model()`.
*   Ensures `controller.close()` is called at the end, possibly using a `try...finally` block.

## 4. Data Flow

1.  `main.py` starts the process, taking user input.
2.  `ContextSearcher` begins its loop.
3.  `ContextSearcher` -> `OllamaController`: "Set context to size X."
4.  `OllamaController` -> `ollama` process: Sends `/set` and `Hello` commands.
5.  `ContextSearcher` -> `OllamaMonitor`: "What is the processor usage?"
6.  `OllamaMonitor` -> `shell`: Runs `ollama ps` and parses the output.
7.  `OllamaMonitor` -> `ContextSearcher`: Returns `"100% GPU"`, `"CPU"`, etc.
8.  `ContextSearcher` adjusts its search range and repeats the loop.
9.  Once the loop terminates, `ContextSearcher` returns the optimal size to `main.py`.
10. `main.py` -> `OllamaController`: "Save the model."
11. `OllamaController` -> `ollama` process: Sends `/save` command.
12. `main.py` -> `OllamaController`: "Close the session."
