import argparse
import sys
from pathlib import Path

from test_harness import harness


def main(argv=None):
    parser = argparse.ArgumentParser(prog="test_harness")
    parser.add_argument("skill", help="<module>/<skill>, e.g. engineering/tdd")
    parser.add_argument("--case", required=True, help="case id from the skill's evals/evals.yaml")
    parser.add_argument("-m", "--model", required=True, help="provider/model passed to opencode -m")
    args = parser.parse_args(argv)

    root = Path.cwd()
    skill_dir = root / args.skill
    evals_file = harness.evals_path(skill_dir)
    if not evals_file.is_file():
        print(f"error: no {args.skill}/evals/evals.yaml", file=sys.stderr)
        return 2

    try:
        case = harness.find_case(harness.load_cases(skill_dir), args.case)
    except KeyError:
        print(f"error: no case '{args.case}' in {args.skill}/evals/evals.yaml", file=sys.stderr)
        return 2

    # Sent verbatim. The "with" arm runs normally (#12), so whether the skill
    # gets loaded is up to the model and is recorded in skills_loaded.
    prompt = case["prompt"]
    try:
        events = harness.run_opencode(prompt, args.model)
    except harness.OpencodeError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    parsed = harness.parse_events(events)
    checks = harness.grade(case.get("checks", []), parsed["output"])
    passed = all(check["passed"] for check in checks)

    record = {
        "skill": args.skill,
        "case": args.case,
        "model": args.model,
        "prompt": prompt,
        "output": parsed["output"],
        "skills_loaded": parsed["skills_loaded"],
        "checks": checks,
        "passed": passed,
    }
    path = harness.write_result(root / "test_harness" / "results", record)

    print(f"{'PASS' if passed else 'FAIL'} {args.skill} {args.case} ({args.model})")
    print(f"result: {path}")
    return 0 if passed else 1
