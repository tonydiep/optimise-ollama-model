import pexpect
import re
import time
import subprocess
import tempfile
import os


class OllamaController:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.child = pexpect.spawn(f"ollama run {model_name}", timeout=60)
        self.child.expect([">%%", ">>> "])  # Expect the actual prompt

    def set_context(self, size: int) -> bool:
        try:
            # Log what we're sending
            command = f"/set parameter num_ctx {size}"
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending to interactive shell: {command}"
            )
            self.child.sendline(command)

            # Wait for a proper response - Ollama interactive mode uses different prompt formats
            try:
                response = self.child.expect([">%%", ">>>"], timeout=10)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received response: {self.child.after}"
                )
            except pexpect.TIMEOUT:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Timeout waiting for response to: {command}"
                )
                return False

            # Send test message
            test_message = "Hello"
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending to interactive shell: {test_message}"
            )
            self.child.sendline(test_message)

            # Wait for response again
            try:
                response2 = self.child.expect([">%%", ">>>"], timeout=10)
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received test response: {self.child.after}"
                )
            except pexpect.TIMEOUT:
                print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Timeout waiting for response to: {test_message}"
                )
                return False

            return True
        except pexpect.ExceptionPexpect as e:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception during set_context: {e}"
            )
            return False

    def save_model(self, context_size: int) -> bool:
        try:
            # First, get the original modelfile
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Retrieving modelfile for {self.model_name}")
            result = subprocess.run(
                ["ollama", "show", "--modelfile", self.model_name],
                capture_output=True,
                text=True,
                check=True,
            )
            original_modelfile = result.stdout
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully retrieved modelfile")

            # Append the new parameter
            new_modelfile_content = f"{original_modelfile.strip()}\nPARAMETER num_ctx {context_size}\n"

            # Create a temporary modelfile
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".modelfile") as tmpfile:
                tmpfile.write(new_modelfile_content)
                modelfile_path = tmpfile.name

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Wrote temporary modelfile to {modelfile_path}")

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
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully created model {self.model_name} with context size {context_size}")
                return True
            else:
                # pexpect child.before contains the output before the match (EOF in this case)
                error_output = child.before.decode() if child.before else "No output"
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 'ollama create' failed. Output: {error_output}")
                return False

        except (pexpect.ExceptionPexpect, subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception during save_model: {e}")
            if 'modelfile_path' in locals() and os.path.exists(modelfile_path):
                os.remove(modelfile_path) # Ensure cleanup on error
            return False


    def close(self):
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
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception while closing: {e}. Force terminating...")
            self.child.terminate(force=True)
        finally:
            if self.child.isalive():
                self.child.close()
