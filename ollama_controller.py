import logging
import os
import pexpect
import re
import subprocess
import tempfile
import time

TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
TIMEFORMAT_SHORT = "%Y-%d %H:%M:%S"

logger = logging.getLogger(__name__)


TIMEOUT_RUN = 120
TIMEOUT_SET = 120
TIMEOUT_PSEND = 30
TIMEOUT_CREATE = 300
TIMEOUT_EXIT = 5


class OllamaController:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.monitor_process = None
        self.child = pexpect.spawn(f"ollama run {model_name}", timeout=TIMEOUT_RUN)
        self.child.expect([">%%", ">>> "])  # Expect the actual prompt

    def set_context(self, size: int) -> tuple[bool, dict]:
        try:
            command = f"/set parameter num_ctx {size}"
            logger.debug(f"Sending to interactive shell: {command}")
            self.child.sendline(command)

            try:
                response = self.child.expect([">%%", ">>>"], timeout=TIMEOUT_SET)
                logger.debug(f"Received response: {self.child.after}")
            except pexpect.TIMEOUT:
                logger.warning(f"Timeout waiting for response to: {command}")
                return (
                    False,
                    {"context_size": None, "processor": None, "success": False},
                )

            test_message = "Hello"
            logger.debug(f"Sending to interactive shell: {test_message}")
            self.child.sendline(test_message)

            try:
                response2 = self.child.expect(
                    [">%%", r">>>\s+\S+"], timeout=TIMEOUT_SET
                )
                logger.debug(f"Received test response: {self.child.after}")
            except pexpect.TIMEOUT:
                logger.warning(f"Timeout waiting for response to: {test_message}")
                return (
                    False,
                    {"context_size": None, "processor": None, "success": False},
                )

            monitor_results = self.monitor_context()
            if monitor_results and monitor_results["success"]:
                context_size_match = monitor_results["context_size"] == size
                logger.debug(
                    f"Context size match: {context_size_match}, Expected: {size}, Actual: {monitor_results['context_size']}, Processor: {monitor_results['processor']}"
                )
                return (True, monitor_results)
            else:
                logger.debug(
                    "Monitor validation failed, returning success without results"
                )
                return (
                    True,
                    {"context_size": None, "processor": None, "success": False},
                )

        except pexpect.ExceptionPexpect as e:
            logger.error(f"Exception during set_context: {e}")
            return (False, {"context_size": None, "processor": None, "success": False})

    def monitor_context(self) -> dict:
        """
        Spawn separate process to run ollama ps and parse output.

        Returns:
            dict: {"context_size": int or None, "processor": str or None, "success": bool}
        """
        try:
            logger.debug("Spawning monitor subprocess for ollama ps")
            result = subprocess.run(
                ["ollama", "ps"], capture_output=True, text=True, timeout=TIMEOUT_PSEND
            )
            logger.debug(
                f"Monitor subprocess completed with return code {result.returncode}"
            )
            logger.debug(f"Monitor stdout: {result.stdout}")
            logger.debug(f"Monitor stderr: {result.stderr}")

            lines = result.stdout.strip().split("\n")
            monitor_result = {"context_size": None, "processor": None, "success": False}

            for line in lines[1:]:  # Skip header
                if self.model_name in line:
                    parts = line.split()
                    processor_part = ""
                    context_size_part = None

                    # From: NAME ID SIZE PROCESSOR CONTEXT UNTIL
                    # After split: [0] [1] [2-3] [4-5] [6] [7]
                    if len(parts) >= 7:
                        # Processor is parts[4] and parts[5]
                        processor_part = " ".join(parts[4:6])
                        # Context size is parts[6]
                        context_size_part = parts[6]

                        logger.debug(f"Monitor found model: {line}")
                        logger.debug(f"Context size: {context_size_part}")
                        logger.debug(f"Processor: {processor_part}")

                        try:
                            context_size = int(context_size_part)
                            monitor_result["context_size"] = context_size
                        except ValueError:
                            logger.debug("Context size not a valid integer")

                        if "GPU" in processor_part and "CPU" not in processor_part:
                            monitor_result["processor"] = "100% GPU"
                        elif "CPU" in processor_part:
                            monitor_result["processor"] = (
                                "MIXED" if "GPU" in processor_part else "CPU"
                            )
                        else:
                            monitor_result["processor"] = None

                        monitor_result["success"] = True
                        break

            if not monitor_result["success"]:
                logger.debug("Model not found in ollama ps output")

            return monitor_result

        except subprocess.TimeoutExpired:
            logger.warning("Monitor subprocess timeout")
            return {"context_size": None, "processor": None, "success": False}
        except subprocess.SubprocessError as e:
            logger.error(f"Subprocess error in monitor_context: {e}")
            return {"context_size": None, "processor": None, "success": False}
        except Exception as e:
            logger.error(f"Exception in monitor_context: {e}")
            return {"context_size": None, "processor": None, "success": False}

    def save_model(self, context_size: int) -> bool:
        modelfile_path: str | None = None

        try:
            logger.info(f"Retrieving modelfile for {self.model_name}")
            result = subprocess.run(
                ["ollama", "show", "--modelfile", self.model_name],
                capture_output=True,
                text=True,
                check=True,
            )
            original_modelfile = result.stdout
            logger.info(f"Successfully retrieved modelfile for {self.model_name}")

            new_modelfile_content = (
                f"{original_modelfile.strip()}\nPARAMETER num_ctx {context_size}\n"
            )

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".modelfile"
            ) as tmpfile:
                tmpfile.write(new_modelfile_content)
                modelfile_path = tmpfile.name

            logger.info(f"Wrote temporary modelfile to {modelfile_path}")

            create_command = f"ollama create {self.model_name} -f {modelfile_path}"
            logger.info(f"Running: {create_command}")

            child = pexpect.spawn(create_command, timeout=TIMEOUT_CREATE)
            child.expect(pexpect.EOF)
            child.close()

            os.remove(modelfile_path)
            modelfile_path = None

            if child.exitstatus == 0:
                logger.info(
                    f"Successfully created model {self.model_name} with context size {context_size}"
                )
                return True
            else:
                error_output = child.before.decode() if child.before else "No output"
                logger.error(f"'ollama create' failed. Output: {error_output}")
                return False

        except (
            pexpect.ExceptionPexpect,
            subprocess.CalledProcessError,
            Exception,
        ) as e:
            logger.error(f"Exception during save_model: {e}")
            if modelfile_path and os.path.exists(modelfile_path):
                os.remove(modelfile_path)
            return False

    def close(self) -> None:
        if self.monitor_process is not None and self.monitor_process.poll() is None:
            logger.warning("Killing monitor subprocess")
            self.monitor_process.kill()

        try:
            command = "/exit"
            logger.debug(f"Sending close command: {command}")
            self.child.sendline(command)

            try:
                self.child.expect(pexpect.EOF, timeout=TIMEOUT_EXIT)
                logger.debug("Received EOF from interactive shell")
            except pexpect.TIMEOUT:
                logger.warning("Close timeout, force terminating")
                self.child.terminate(force=True)

        except pexpect.ExceptionPexpect as e:
            logger.error(f"Exception while closing: {e}")
            try:
                self.child.terminate(force=True)
            except Exception:
                pass
        finally:
            try:
                if self.child is not None and self.child.isalive():
                    self.child.close()
            except Exception:
                pass
