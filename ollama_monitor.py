import subprocess


class OllamaMonitor:
    @staticmethod
    def get_processor_usage(model_name: str) -> str:
        try:
            result = subprocess.run(['ollama', 'ps'], capture_output=True, text=True, timeout=30)
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:
                if model_name in line:
                    parts = line.split()
                    processor_part = parts[3] if len(parts) > 3 else ''
                    if 'GPU' in processor_part and 'CPU' not in processor_part:
                        return '100% GPU'
                    elif 'CPU' in processor_part:
                        return 'MIXED' if 'GPU' in processor_part else 'CPU'
                    break
            return 'NOT_FOUND'
        except Exception:
            return 'NOT_FOUND'
