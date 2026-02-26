import logging
import time
from ollama_controller import OllamaController

TIMEFORMAT = "%Y-%m-%d %H:%M:%S"


def _log(message: str) -> None:
    logger.info(f"[{time.strftime(TIMEFORMAT)}] {message}")


logger = logging.getLogger(__name__)


class ContextSearcher:
    def __init__(self, controller: OllamaController) -> None:
        self.controller = controller

    def find_optimal_size(self, min_size: int, max_size: int) -> int:
        """
        Implements the binary search algorithm to find the optimal context size.

        Args:
            min_size: The minimum context size to search from
            max_size: The maximum context size to search to

        Returns:
            The optimal context size that fits entirely on GPU
        """
        logger.info(f"Starting context optimization search")
        logger.info(f"Model: {self.controller.model_name}")
        logger.info(f"Search range: {min_size} to {max_size}")

        logger.info(f"Trying maximum size {max_size} first as optimal size")

        # Set the maximum context size and attempt to run with it
        success, monitor_results = self.controller.set_context(max_size)
        if success:
            # Monitor validation already provides processor info
            processor = monitor_results.get("processor", "NOT_FOUND")
            _log(f"Model processor for max size {max_size}: {processor}")

            # If the maximum size works correctly on GPU, use it as optimal size
            if processor == "100% GPU":
                _log(f"Maximum size {max_size} works correctly on GPU")
                return max_size
            # If using maximum size caused the model to run on CPU/MIXED, continue to binary search
            # If there was an error, we also continue to binary search
        else:
            _log(f"Failed to set maximum size {max_size}, continuing to binary search")

        # If maximum size doesn't work, fall back to binary search with proper crash handling
        low = min_size
        high = max_size
        last_good_size = min_size

        _log(f"Starting binary search with range {min_size} to {max_size}")

        while low <= high:
            mid = (low + high) // 2
            _log(f"Testing context size: {mid}")

            success, monitor_results = self.controller.set_context(mid)
            if not success:
                _log(f"Failed to set context size {mid}, skipping...")
                high = mid - 1
                continue

            processor = monitor_results.get("processor", "NOT_FOUND")
            _log(f"Model processor for size {mid}: {processor}")

            if processor == "100% GPU":
                last_good_size = mid
                low = mid + 1

                if (high - low) < 1000:
                    _log("Early exit condition met, stopping search")
                    break
            elif processor == "CPU" or processor == "MIXED":
                high = mid - 1
            else:
                _log(f"Model processor not found for size {mid}, trying smaller size")
                high = mid - 1

        _log(f"Binary search completed, optimal size: {last_good_size}")
        return last_good_size
