#!/usr/bin/env python3
"""
Test router skills from the command line.

Usage:
  python3 skill_test.py <skill_name> [param=value ...]

Examples:
  python3 skill_test.py mongchoi_query query=race race_date=2026/02/25 race_no=1 horse_no=3
  python3 skill_test.py hello_world
  python3 skill_test.py create_post platform="LinkedIn" text="Hello world!"
"""
import argparse
import importlib
import json
import os
import sys

# Ensure router/ is on path when run from router/skills/
_script_dir = os.path.dirname(os.path.abspath(__file__))
_router_dir = os.path.dirname(_script_dir)
if _router_dir not in sys.path:
    sys.path.insert(0, _router_dir)


def parse_params(args: list[str]) -> dict:
    """Parse key=value pairs. Values may be quoted: key="value with spaces"."""
    params = {}
    for a in args:
        if "=" not in a:
            continue
        idx = a.index("=")
        key = a[:idx].strip()
        value = a[idx + 1 :].strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        params[key] = value
    return params


def get_skill_class(skill_name: str):
    """Load skill class: mongchoi_query -> MongchoiQuerySkill."""
    module_name = skill_name.lower().replace("-", "_")
    class_name = "".join(w.capitalize() for w in module_name.split("_")) + "Skill"
    module_path = f"skills.{module_name}.skill"
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def main():
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Test router skills from the command line.",
        epilog="""
Examples:
  python3 skill_test.py mongchoi_query query=race race_date=2026/02/25 race_no=1
  python3 skill_test.py hello_world
  python3 skill_test.py create_post platform="LinkedIn" text="Hello world!"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("skill", help="Skill name (e.g. mongchoi_query, hello_world, create_post)")
    parser.add_argument(
        "params",
        nargs="*",
        metavar="param=value",
        help='Params as key=value. Use quotes for values with spaces: text="Hello world!"',
    )
    args = parser.parse_args()

    params = parse_params(args.params)

    try:
        SkillClass = get_skill_class(args.skill)
        skill = SkillClass()
        result = skill.execute(params)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
