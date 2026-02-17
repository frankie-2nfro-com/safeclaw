"""
Chat loop: user input -> prompt.py -> Ollama -> print response -> loop
Self-contained agent. Run from agent/: python chat.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure agent dir is in path when run from anywhere
_agent_dir = Path(__file__).resolve().parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

import ollama
from dotenv import load_dotenv

from libs.prompt import Prompt
from libs.llm_response import LLMResponse, LLMResponseError
from libs.action_executor import ActionExecutor

WORKSPACE = _agent_dir / "workspace"

# Default content for workspace files (created if missing)
WORKSPACE_DEFAULTS = {
    "memory.json": {},
    "input_history.json": [],
    "artifact.json": {},
}

# Copy from initial template if runtime file missing
WORKSPACE_INITIAL_TEMPLATES = {
    "agent_action.json": "agent_action_initial.json",
    "router_actions.json": "router_actions_initial.json",
    "SOUL.md": "SOUL_initial.md",
}


def ensure_workspace_files():
    """Create workspace files if missing. Use {}/[] for data files; copy from *_initial.json for action configs."""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    for filename, default in WORKSPACE_DEFAULTS.items():
        path = WORKSPACE / filename
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
    for target, source in WORKSPACE_INITIAL_TEMPLATES.items():
        target_path = WORKSPACE / target
        source_path = WORKSPACE / source
        if not target_path.exists() and source_path.exists():
            target_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")


def main():
    load_dotenv(_agent_dir / ".env")
    ensure_workspace_files()
    prompt_builder = Prompt(workspace=WORKSPACE)
    model = "llama3.1:8B"

    print("\n" + "=" * 60)
    print(f"  SafeClaw Chat (Ollama + {model})")
    print("  Type 'quit' or 'exit' to stop")
    print("=" * 60 + "\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        # load input history
        input_history = []
        with open(WORKSPACE / "input_history.json", "r") as f:
            input_history = json.load(f)

        # 1. Generate prompt from template (SOUL, MEMORY, ARTIFACT, etc.)
        prompt = prompt_builder.create_prompt(user_input)
        if not prompt:
            print("(Empty prompt, skipping)\n")
            continue

        # 2. Send to llm (Ollama)
        try:
            response = ollama.chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            output = response.message.content
        except Exception as e:
            output = f"Error: {e}"
            print("(Make sure Ollama is running: ollama serve, ollama pull mistral)")

        # 3. Parse and print output
        try:
            resp = LLMResponse(output)
            print(f"\nSafeClaw: {resp.message}")
            print(f"Actions: {resp.actions}")

            if resp.actions:
                artifact = {
                    "timestamp": datetime.now().isoformat(),
                    "data": []
                }

                for action in resp.actions:
                    try:
                        action_name = action["name"]
                        params = action["params"]
                        executor = ActionExecutor(action_name, params, workspace=WORKSPACE)
                        executed_result = executor.execute()
                        artifact["data"].append({"data": executed_result})
                    except Exception as e:
                        print(f"Error: {e}")

                follow_up_results = []
                for follow_info in artifact["data"]:
                    if "data" in follow_info and follow_info["data"] is not None and "follow_up" in follow_info["data"]:
                        try:
                            follow_up_action = follow_info["data"]["follow_up"]
                            follow_up_action_name = follow_up_action["name"]
                            follow_up_action_params = follow_up_action["params"]
                            follow_up_action_executor = ActionExecutor(
                                follow_up_action_name, follow_up_action_params, workspace=WORKSPACE
                            )
                            follow_up_action_result = follow_up_action_executor.execute()
                            follow_up_results.append(follow_up_action_result)
                            print(f"\nSafeClaw: {follow_up_action_result['output']}")

                            input_history.append(
                                {
                                    "follow_up_action": follow_up_action["name"],
                                    "response": follow_up_action_result['output']
                                }
                            )
                        except Exception as e:
                            print(f"Follow up encountered error. Just skip it...")

                artifact["follow_up_results"] = follow_up_results

                with open(WORKSPACE / "artifact.json", "w") as f:
                    json.dump(artifact, f, indent=2)

            print()
        except LLMResponseError as e:
            print(f"\nSafeClaw: (Parse error: {e})\n")

        # 4. add user_input to input_history.json
        input_history.append(
            {"user_input": user_input, "response": resp.message}
        )
        if len(input_history) > 10:
            input_history = input_history[-10:]
        with open(WORKSPACE / "input_history.json", "w") as f:
            json.dump(input_history, f, indent=2)


if __name__ == "__main__":
    main()
