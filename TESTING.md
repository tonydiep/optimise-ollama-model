# Testing Strategy: Ollama Context Optimizer

This document outlines the testing strategy for the Ollama Context Optimizer project. The strategy includes unit tests, integration tests, and manual testing to ensure the application is robust, reliable, and correct.

## 1. Unit Tests

Unit tests will focus on testing individual components in isolation. Mocking will be heavily used to simulate external dependencies like the Ollama processes.

**Location:** `tests/` directory.
**Framework:** `pytest`

### 1.1. `tests/test_ollama_monitor.py`

**Objective:** To verify that the `OllamaMonitor` correctly parses various outputs from the `ollama ps` command.

*   **Test Case 1: Ideal GPU Usage**
    *   **Input:** Mock `ollama ps` output where the target model shows "100% GPU".
    *   **Expected Output:** `get_processor_usage` returns `"100% GPU"`.

*   **Test Case 2: CPU Usage**
    *   **Input:** Mock output where the target model shows "100% CPU".
    *   **Expected Output:** `get_processor_usage` returns `"CPU"`.

*   **Test Case 3: Mixed CPU/GPU Usage**
    *   **Input:** Mock output showing a percentage of CPU (e.g., "43% CPU").
    *   **Expected Output:** `get_processor_usage` returns `"MIXED"`.

*   **Test Case 4: Model Not Found**
    *   **Input:** Mock output where the target model is not in the list.
    *   **Expected Output:** `get_processor_usage` returns `"NOT_FOUND"`.

*   **Test Case 5: Empty `ollama ps` Output**
    *   **Input:** Mock command returns an empty string.
    *   **Expected Output:** `get_processor_usage` returns `"NOT_FOUND"`.

*   **Test Case 6: Malformed Output**
    *   **Input:** Mock output with unexpected formatting.
    *   **Expected Behavior:** The function should handle the error gracefully and return `"NOT_FOUND"` or raise a specific parsing error.

### 1.2. `tests/test_context_searcher.py`

**Objective:** To verify the binary search algorithm in `ContextSearcher` works correctly based on simulated monitor feedback.

*   The `OllamaController` will be a simple mock object.
*   The `OllamaMonitor`'s `get_processor_usage` method will be mocked to return different values based on the input context size.

*   **Test Case 1: Simple Binary Search**
    *   **Scenario:** The monitor mock returns `"100% GPU"` for sizes `< 5000` and `"CPU"` for sizes `>= 5000`.
    *   **Range:** `[0, 10000]`
    *   **Expected Result:** The search should converge and return a value close to `4999`.

*   **Test Case 2: Early Exit Condition**
    *   **Scenario:** The monitor mock is configured to always return `"100% GPU"`. The search range is `[0, 20000]`.
    *   **Expected Behavior:** The search should not run to completion. It should stop and return a valid size once the difference between `high` and `low` becomes less than 1000.

*   **Test Case 3: No GPU Fit**
    *   **Scenario:** The monitor mock always returns `"CPU"`.
    *   **Range:** `[1000, 10000]`
    *   **Expected Result:** The search should return the initial `min_size` (or a designated failure value like `0` or `-1`).

## 2. Integration Tests

Integration tests will verify that the components work together. These tests are more complex and may require a running Ollama instance.

### 2.1. `tests/test_ollama_controller_integration.py`

**Objective:** To ensure the `OllamaController` can successfully communicate with a real `ollama run` process.

**Prerequisite:** A running Ollama service and a small, fast-loading model (e.g., `tinyllama`). This requirement should be clearly documented for anyone running the tests.

*   **Test Case 1: Initialization**
    *   **Action:** Create an `OllamaController` instance.
    *   **Expected Behavior:** The controller successfully starts the `ollama run tinyllama` process and detects the initial prompt.

*   **Test Case 2: Set Context**
    *   **Action:** Call `set_context(128)` on the controller.
    *   **Expected Behavior:** The command is sent, and the controller successfully detects the subsequent prompt, returning `True`.

*   **Test Case 3: Save Model (Mocked)**
    *   While a full save is a heavy operation, a test can send the `/save` command and check if the process responds as expected without waiting for the full save to complete.

## 3. Manual Testing

**Objective:** To perform an end-to-end test of the entire application with a real-world model.

**Procedure:**

1.  **Setup:**
    *   Ensure Python environment is set up.
    *   Ensure Ollama is running.
    *   Choose a target model (e.g., `qwen3-30b-abliterated-custom`).
    *   Choose a wide search range (e.g., `--min 1000 --max 80000`).

2.  **Execution:**
    *   Run the main script: `python main.py --model [model_name] --min [min] --max [max]`.

3.  **Verification:**
    *   **Observe Logs:** The application should log its progress, including the context size it's trying and the result from `ollama ps`.
    *   **Check `ollama ps`:** Manually run `ollama ps` in another terminal to confirm the application's findings.
    *   **Final Result:**
        *   Verify that the application terminates and reports an optimal context size.
        *   Verify that the `ollama` process for saving the new model is triggered.
        *   Run `ollama list` to confirm that the new, saved model appears.
        *   Run the new model (`ollama run [model_name]-optimized`) and check its context size to confirm the optimization was successful.
