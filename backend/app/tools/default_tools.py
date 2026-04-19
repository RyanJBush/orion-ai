import re

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
