import pexpect
import re


class OllamaController:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.child = pexpect.spawn(f'ollama run {model_name}', timeout=60)
        self.child.expect('>>>')

    def set_context(self, size: int) -> bool:
        try:
            self.child.sendline(f'/set parameter num_ctx {size}')
            self.child.expect('>%%')
            self.child.sendline('Hello')
            self.child.expect('>%%')
            return True
        except pexpect.ExceptionPexpect:
            return False

    def save_model(self) -> bool:
        try:
            self.child.sendline(f'/save {self.model_name}')
            index = self.child.expect([pexpect.TIMEOUT, r'Created new model.*', '>%%'], timeout=120)
            if index == 1:
                return True
            return False
        except pexpect.ExceptionPexpect:
            return False

    def close(self):
        try:
            self.child.sendline('/exit')
            self.child.close()
        except Exception:
            pass
