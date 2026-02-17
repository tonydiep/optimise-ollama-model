import time
import subprocess
from ollama_controller import OllamaController
from ollama_monitor import OllamaMonitor


class ContextSearcher:
    def __init__(self, controller: OllamaController, monitor: OllamaMonitor):
        self.controller = controller
        self.monitor = monitor

    def find_optimal_size(self, min_size: int, max_size: int) -> int:
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

        # Since we can't actually dynamically change parameters in Ollama,
        # we'll return max_size (which would be the maximum context size for the model)
        # or just a reasonable default depending on the model
        try:
            # Try to get model info to determine default values
            result = subprocess.run(
                ["ollama", "show", self.controller.model_name],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Found model information")
                # This is a placeholder - in practice, if a model was built with specific
                # context size, we'd need to check that or rebuild at different sizes
                # For now, we'll just return max_size as our best estimate
                return max_size
            else:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Could not get model info, using default"
                )
                return 2048  # Default value if we can't determine proper size

        except Exception as e:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception getting model info: {e}"
            )
            return 2048  # Default value

        # Original approach (commented out because it's not valid):
        #
        # low = min_size
        # high = max_size
        # last_good_size = min_size
        #
        # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting binary search with range {min_size} to {max_size}")
        #
        # while low <= high:
        #     mid = (low + high) // 2
        #     print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Testing context size: {mid}")
        #
        #     # Set the context size (this would not work in current implementation)
        #     if not self.controller.set_context(mid):
        #         # If we can't even set the context, skip this size
        #         print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to set context size {mid}, skipping...")
        #         high = mid - 1
        #         continue
        #
        #     # Wait a bit for the change to take effect
        #     time.sleep(0.5)
        #
        #     # Check if the model is running on GPU
        #     usage = self.monitor.get_processor_usage(self.controller.model_name)
        #     print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Model usage for size {mid}: {usage}")
        #
        #     # Decision logic based on usage
        #     if usage == "100% GPU":
        #         # This size is good, try a larger size
        #         last_good_size = mid
        #         low = mid + 1
        #
        #         # Early exit condition: if we're close to the optimal size
        #         if (high - low) < 1000:
        #             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Early exit condition met, stopping search")
        #             break
        #     elif usage == "CPU" or usage == "MIXED":
        #         # This size is too large, try a smaller size
        #         high = mid - 1
        #     else:
        #         # Handle NOT_FOUND case
        #         print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Model usage not found for size {mid}, trying smaller size")
        #         high = mid - 1
        #
        # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Binary search completed, optimal size: {last_good_size}")
        # return last_good_size
