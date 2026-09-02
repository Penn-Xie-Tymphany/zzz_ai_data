"""Run the agent on a single DataAgent-Bench task.

Usage:
    python scripts/run_task.py --task-dir ../../competitions/datasets/public/input/task_11 --question "..."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from penn_data_agent.agent import ReActAgent
from penn_data_agent.llm import LLMClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--question", required=True)
    args = parser.parse_args()

    agent = ReActAgent(llm=LLMClient(), tools=[], system_prompt="You are a ReAct data agent.")
    print(agent.run(args.question, str(Path(args.task_dir))))


if __name__ == "__main__":
    main()
