import unittest
from unittest.mock import patch, MagicMock
from ollama_monitor import OllamaMonitor


class TestOllamaMonitor(unittest.TestCase):
    def test_get_processor_usage_actual_format(self):
        """Test parsing with actual ollama ps output format - GPU case"""
        # This matches the real output format where "100% GPU" is split between columns
        mock_output = """NAME                         ID              SIZE      PROCESSOR    CONTEXT    UNTIL               
granite4-custom:latest       500c8be7a076    2.4 GB    100% GPU     4343       59 minutes from now    
qwen3-coder-custom:latest    2478a3f7c98a    34 GB     100% GPU     262144     58 minutes from now    """

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            monitor = OllamaMonitor()
            result = monitor.get_processor_usage("granite4-custom:latest")
            self.assertEqual(result, "100% GPU")

    def test_get_processor_usage_actual_format_cpu(self):
        """Test parsing with actual ollama ps output format - CPU case"""
        # For a CPU case, we need to test that our logic properly identifies that
        mock_output = """NAME                         ID              SIZE      PROCESSOR    CONTEXT    UNTIL               
granite4-custom:latest       500c8be7a076    2.4 GB    100% GPU     4343       59 minutes from now    
qwen3-coder-custom:latest    2478a3f7c98a    34 GB     100% CPU     262144     58 minutes from now    """

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            monitor = OllamaMonitor()
            result = monitor.get_processor_usage("qwen3-coder-custom:latest")
            self.assertEqual(result, "CPU")

    def test_get_processor_usage_not_found(self):
        """Test when model is not found"""
        mock_output = """NAME                         ID              SIZE      PROCESSOR    CONTEXT    UNTIL               
other-model   ollama run           2 hours ago         running             1                  100% GPU"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            monitor = OllamaMonitor()
            result = monitor.get_processor_usage("qwen3-30b-abliterated-custom")
            self.assertEqual(result, "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
