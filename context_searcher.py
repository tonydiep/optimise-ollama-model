import time
from ollama_controller import OllamaController
from ollama_monitor import OllamaMonitor

class ContextSearcher:
    def __init__(self, controller: OllamaController, monitor: OllamaMonitor):
        self.controller = controller
        self.monitor = monitor

    def find_optimal_size(self, min_size: int, max_size: int) -> int:
        """
        Implements the binary search algorithm to find the optimal context size.
        
        Args:
            min_size: The minimum context size to search from
            max_size: The maximum context size to search to
            
        Returns:
            The optimal context size that fits entirely on GPU
        """
        low = min_size
        high = max_size
        last_good_size = min_size
        
        while low <= high:
            mid = (low + high) // 2
            
            # Set the context size
            if not self.controller.set_context(mid):
                # If we can't even set the context, skip this size
                high = mid - 1
                continue
                
            # Wait a bit for the change to take effect
            time.sleep(0.5)
            
            # Check if the model is running on GPU
            usage = self.monitor.get_processor_usage(self.controller.model_name)
            
            # Decision logic based on usage
            if usage == "100% GPU":
                # This size is good, try a larger size
                last_good_size = mid
                low = mid + 1
                
                # Early exit condition: if we're close to the optimal size
                if (high - low) < 1000:
                    break
            elif usage == "CPU" or usage == "MIXED":
                # This size is too large, try a smaller size
                high = mid - 1
            else:
                # Handle NOT_FOUND case
                high = mid - 1
                
        return last_good_size