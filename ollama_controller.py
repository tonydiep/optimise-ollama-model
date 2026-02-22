import pexpect
import re
import time
import subprocess
import tempfile
import os


class OllamaController:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.monitor_process = None
        self.child = pexpect.spawn(f"ollama run {model_name}", timeout=120)
        self.child.expect([">%%", ">>> "])  # Expect the actual prompt

    def set_context(self, size: int) -> tuple[bool, dict]:
        try:
            # Log what we're sending
            command = f"/set parameter num_ctx {size}"
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending to interactive shell: {command}"
            )
            self.child.sendline(command)

            # Wait for a proper response - Ollama interactive mode uses different prompt formats
            try:
                response = self.child.expect([">%%", ">>>"], timeout=120)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received response: {self.child.after}"
                )
            except pexpect.TIMEOUT:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Timeout waiting for response to: {command}"
                )
                return (False, {"context_size": None, "processor": None, "success": False})

            # Send test message
            test_message = "Hello"
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending to interactive shell: {test_message}"
            )
            self.child.sendline(test_message)

            # Wait for response again - after "Hello" we expect ">>> " followed by some text
            try:
                # Wait for the prompt followed by some content (to indicate command completion)
                response2 = self.child.expect([">%%", r">>>\s+\S+"], timeout=120)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received test response: {self.child.after}"
                )
            except pexpect.TIMEOUT:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Timeout waiting for response to: {test_message}"
                )
                return (False, {"context_size": None, "processor": None, "success": False})

            # Step 4.5: Validate context with monitor
            monitor_results = self.monitor_context()
            if monitor_results and monitor_results["success"]:
                context_size_match = (monitor_results["context_size"] == size)
                print(f"[DEBUG] Context size match: {context_size_match}")
                print(f"[DEBUG] Expected: {size}, Actual: {monitor_results['context_size']}")
                print(f"[DEBUG] Processor: {monitor_results['processor']}")
                return (True, monitor_results)
            else:
                print("[DEBUG] Monitor validation failed, returning success without results")
                return (True, {"context_size": None, "processor": None, "success": False})

        except pexpect.ExceptionPexpect as e:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception during set_context: {e}"
            )
            return (False, {"context_size": None, "processor": None, "success": False})

    def monitor_context(self) -> dict:
        """
        Spawn separate process to run ollama ps and parse output.

        Returns:
            dict: {"context_size": int or None, "processor": str or None, "success": bool}
        """
        try:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Spawning monitor subprocess for ollama ps..."
            )
            result = subprocess.run(
                ["ollama", "ps"], capture_output=True, text=True, timeout=30
            )
            print(
                f"[{time.strftime('%Y-%d %H:%M:%S')}] Monitor subprocess completed with return code {result.returncode}"
            )
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitor stdout: {result.stdout}")
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitor stderr: {result.stderr}")

            lines = result.stdout.strip().split("\n")
            monitor_result = {
                "context_size": None,
                "processor": None,
                "success": False
            }

            for line in lines[1:]:  # Skip header
                if self.model_name in line:
                    parts = line.split()
                    processor_part = ""
                    context_size_part = None

                    if len(parts) >= 6:
                        context_size_part = parts[4]
                        processor_part = " ".join(parts[5:])

                        print(f"[DEBUG] Monitor found model: {line}")
                        print(f"[DEBUG] Context size: {context_size_part}")
                        print(f"[DEBUG] Processor: {processor_part}")

                        # Parse context size
                        try:
                            context_size = int(context_size_part)
                            monitor_result["context_size"] = context_size
                        except ValueError:
                            print("[DEBUG] Context size not a valid integer")

                        # Parse processor
                        if "GPU" in processor_part and "CPU" not in processor_part:
                            monitor_result["processor"] = "100% GPU"
                        elif "CPU" in processor_part:
                            monitor_result["processor"] = "MIXED" if "GPU" in processor_part else "CPU"
                        else:
                            monitor_result["processor"] = None

                        monitor_result["success"] = True
                        break

            if not monitor_result["success"]:
                print("[DEBUG] Model not found in ollama ps output")

            return monitor_result

        except subprocess.TimeoutExpired:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Monitor subprocess timeout"
            )
            return {
                "context_size": None,
                "processor": None,
                "success": False
            }
        except Exception as e:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception in monitor_context: {e}"
            )
            return {
                "context_size": None,
                "processor": None,
                "success": False
            }

    def save_model(self, context_size: int) -> bool:
        modelfile_path = None  # Initialize the variable

        try:
            # First, get the original modelfile
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Retrieving modelfile for {self.model_name}"
            )
            result = subprocess.run(
                ["ollama", "show", "--modelfile", self.model_name],
                capture_output=True,
                text=True,
                check=True,
            )
            original_modelfile = result.stdout
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully retrieved modelfile"
            )

            # Append the new parameter
            new_modelfile_content = (
                f"{original_modelfile.strip()}\nPARAMETER num_ctx {context_size}\n"
            )

            # Create a temporary modelfile
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".modelfile"
            ) as tmpfile:
                tmpfile.write(new_modelfile_content)
                modelfile_path = tmpfile.name

            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Wrote temporary modelfile to {modelfile_path}"
            )

            # Create the new model
            create_command = f"ollama create {self.model_name} -f {modelfile_path}"
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running: {create_command}")

            child = pexpect.spawn(create_command, timeout=300)
            # Expecting EOF is a good way to wait for the command to finish
            child.expect(pexpect.EOF)
            child.close()

            # Clean up the temporary file
            os.remove(modelfile_path)

            if child.exitstatus == 0:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully created model {self.model_name} with context size {context_size}"
                )
                return True
            else:
                # pexpect child.before contains the output before the match (EOF in this case)
                error_output = child.before.decode() if child.before else "No output"
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 'ollama create' failed. Output: {error_output}"
                )
                return False

        except (
            pexpect.ExceptionPexpect,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception during save_model: {e}"
            )
            # Clean up the temporary file if it was created
            if modelfile_path and os.path.exists(modelfile_path):
                os.remove(modelfile_path)  # Ensure cleanup on error
            return False

    def close(self):
        # Ensure monitor subprocess is killed if still running
        if self.monitor_process and self.monitor_process.poll() is None:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Killing monitor subprocess..."
            )
            self.monitor_process.kill()
        try:
            # Send exit command to the interactive shell
            command = "/exit"
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending to interactive shell: {command}"
            )
            self.child.sendline(command)

            # Give it a moment to process the exit command
            try:
                self.child.expect(pexpect.EOF, timeout=5)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received EOF from interactive shell"
                )
            except pexpect.TIMEOUT:
                # If it doesn't exit cleanly, force terminate
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Interactive shell exit timeout, force terminating..."
                )
                self.child.terminate(force=True)

        except pexpect.ExceptionPexpect as e:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception while closing: {e}. Force terminating..."
            )
            self.child.terminate(force=True)
        finally:
            if self.child.isalive():
                self.child.close()
