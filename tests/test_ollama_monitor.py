import unittest
from unittest.mock import patch, MagicMock
from ollama_monitor import OllamaMonitor

class TestOllamaMonitor(unittest.TestCase):
    
    def test_get_processor_usage_gpu(self):
        """Test parsing of 100% GPU usage"""
        mock_output = """NAME                 COMMAND              CREATED             STATUS              GPUS               PROCESSOR
qwen3-30b-abliterated-custom   ollama run           2 hours ago         running             1                  100% GPU"""

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            monitor = OllamaMonitor()
            result = monitor.get_processor_usage('qwen3-30b-abliterated-custom')
            self.assertEqual(result, "100% GPU")
            
    def test_get_processor_usage_cpu(self):
        """Test parsing of CPU usage"""
        mock_output = """NAME                 COMMAND              CREATED             STATUS              GPUS               PROCESSOR
qwen3-30b-abliterated-custom   ollama run           2 hours ago         running             1                  100% CPU"""
            
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            monitor = OllamaMonitor()
            result = monitor.get_processor_usage('qwen3-30b-abliterated-custom')
            self.assertEqual(result, "CPU")
            
    def test_get_processor_usage_mixed(self):
        """Test parsing of mixed CPU/GPU usage"""
        mock_output = """NAME                 COMMAND              CREATED             STATUS              GPUS               PROCESSOR
qwen3-30b-abliterated-custom   ollama run           2 hours ago         running             1                  43% CPU"""
            
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            monitor = OllamaMonitor()
            result = monitor.get_processor_usage('qwen3-30b-abliterated-custom')
            self.assertEqual(result, "MIXED")
            
    def test_get_processor_usage_not_found(self):
        """Test when model is not found"""
        mock_output = """NAME                 COMMAND              CREATED             STATUS              GPUS               PROCESSOR
other-model   ollama run           2 hours ago         running             1                  100% GPU"""
            
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)
            monitor = OllamaMonitor()
            result = monitor.get_processor_usage('qwen3-30b-abliterated-custom')
            self.assertEqual(result, "NOT_FOUND")

if __name__ == '__main__':
    unittest.main()