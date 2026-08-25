"""ReAct JSON protocol: constrain model output and parse it robustly."""

from __future__ import annotations

import json
import re

JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def build_output_instruction() -> str:
    return (
        "Respond with ONLY one JSON object:\n"
        '{"step_index": <int>, "thought": "<reasoning>", '
        '"action": "<tool_name|answer>", "action_input": {<dict>}}\n'
        'To finish, use action="answer" with action_input={"final_answer": "<answer>"}'
    )


def parse_action(text: str) -> dict | None:
    match = JSON_BLOCK.search(text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj.get("action"), str):
        return None
    return obj
