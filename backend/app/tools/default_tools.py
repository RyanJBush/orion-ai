import re
import time

from app.tools.base import Tool


class EchoTool(Tool):
    name = "echo"

    def run(self, input_text: str) -> str:
        return input_text


class MathTool(Tool):
    name = "math"

    def run(self, input_text: str) -> str:
        nums = [float(match) for match in re.findall(r"-?\d+(?:\.\d+)?", input_text)]
        if not nums:
            return "No numeric values found."
        return f"sum={sum(nums)}"


class SlowEchoTool(Tool):
    name = "slow_echo"

    def run(self, input_text: str) -> str:
        time.sleep(0.2)
        return f"slow:{input_text}"


class FlakyTool(Tool):
    name = "flaky"

    def __init__(self) -> None:
        self._attempts: dict[str, int] = {}

    def run(self, input_text: str) -> str:
        attempt = self._attempts.get(input_text, 0) + 1
        self._attempts[input_text] = attempt
        if attempt == 1:
            raise RuntimeError("transient_failure")
        return f"recovered:{input_text}"
