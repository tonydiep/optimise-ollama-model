import subprocess
import time


class OllamaMonitor:
    @staticmethod
    def get_processor_usage(model_name: str) -> str:
        try:
            # Give Ollama a moment to start the model
            time.sleep(0.5)

            result = subprocess.run(
                ["ollama", "ps"], capture_output=True, text=True, timeout=30
            )
            lines = result.stdout.strip().split("\n")

            # Print debug information
            print(f"[DEBUG] Ollama ps output: {result.stdout}")

            for line in lines[1:]:
                if model_name in line:
                    parts = line.split()
                    # The processor info is spread across parts[4] and parts[5] for "100% GPU"
                    # For cases like "100% GPU", we need to join the parts to get full processor info
                    processor_part = ""
                    if len(parts) > 5:
                        processor_part = parts[4] + " " + parts[5]
                    elif len(parts) > 4:
                        processor_part = parts[4]
                    print(f"[DEBUG] Found model: {line}")
                    print(f"[DEBUG] Processor part: {processor_part}")
                    # Handle case where we might get only "GB" instead of full processor info
                    if not processor_part or processor_part == "GB":
                        print(
                            "[DEBUG] Processor part appears malformed, trying alternative parsing"
                        )
                        # Try to parse more carefully for the actual GPU info
                        line_parts = line.split()
                        if len(line_parts) >= 6:
                            # Return NOT_FOUND if we can't properly determine GPU usage
                            return "NOT_FOUND"
                    if "GPU" in processor_part and "CPU" not in processor_part:
                        return "100% GPU"
                    elif "CPU" in processor_part:
                        return "MIXED" if "GPU" in processor_part else "CPU"
                    else:
                        # If we can't determine processor usage, default to NOT_FOUND
                        return "NOT_FOUND"
            return "NOT_FOUND"
        except Exception as e:
            print(f"[DEBUG] Exception in get_processor_usage: {e}")
            return "NOT_FOUND"
