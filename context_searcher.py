import time
import subprocess
from ollama_controller import OllamaController
from ollama_monitor import OllamaMonitor


class ContextSearcher:
    def __init__(self, controller: OllamaController, monitor: OllamaMonitor):
        self.controller = controller
        self.monitor = monitor

    def find_optimal_size(self, min_size: int, max_size: int) -> int:
        # opencode: go back to original approach. it is valid. you _CAN_ change context size after model load.

        """
        Implements the binary search algorithm to find the optimal context size.
        Note: This is a simplified approach since Ollama doesn't support dynamically
        changing context size parameters after model load.

        Args:
            min_size: The minimum context size to search from
            max_size: The maximum context size to search to

        Returns:
            The optimal context size that fits entirely on GPU (this is a simplified approach)
        """
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting context optimization search"
        )
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Model: {self.controller.model_name}"
        )
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Search range: {min_size} to {max_size}"
        )

        # First, try using the maximum size as the optimal size
        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Trying maximum size {max_size} first as optimal size"
        )

        # Set the maximum context size and attempt to run with it
        if self.controller.set_context(max_size):
            # Wait a bit for the change to take effect
            time.sleep(0.5)

            # Check if the model is running on GPU
            usage = self.monitor.get_processor_usage(self.controller.model_name)
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Model usage for max size {max_size}: {usage}"
            )

            # If the maximum size works correctly on GPU, use it as optimal size
            if usage == "100% GPU":
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Maximum size {max_size} works correctly on GPU"
                )
                return max_size
            # If using maximum size caused the model to run on CPU/MIXED, continue to binary search
            # If there was an error, we also continue to binary search
        else:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to set maximum size {max_size}, continuing to binary search"
            )

        # If maximum size doesn't work, fall back to binary search with proper crash handling
        low = min_size
        high = max_size
        last_good_size = min_size

        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting binary search with range {min_size} to {max_size}"
        )

        while low <= high:
            mid = (low + high) // 2
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Testing context size: {mid}")

            # Set the context size (this is valid now according to comments)
            if not self.controller.set_context(mid):
                # If we can't even set the context, skip this size
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to set context size {mid}, skipping..."
                )
                high = mid - 1
                continue

            # Wait a bit for the change to take effect
            time.sleep(0.5)

            # Check if the model is running on GPU
            usage = self.monitor.get_processor_usage(self.controller.model_name)
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Model usage for size {mid}: {usage}"
            )

            # Decision logic based on usage
            if usage == "100% GPU":
                # This size is good, try a larger size
                last_good_size = mid
                low = mid + 1

                # Early exit condition: if we're close to the optimal size
                if (high - low) < 1000:
                    print(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Early exit condition met, stopping search"
                    )
                    break
            elif usage == "CPU" or usage == "MIXED":
                # This size is too large, try a smaller size
                high = mid - 1
            else:
                # Handle NOT_FOUND case
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Model usage not found for size {mid}, trying smaller size"
                )
                high = mid - 1

        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Binary search completed, optimal size: {last_good_size}"
        )
        return last_good_size

        # opencode: go back to original approach. it is valid. you _CAN_ change context size after model load.
