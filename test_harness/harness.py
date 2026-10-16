import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml


def evals_path(skill_dir):
    # The one place that knows where a skill's eval cases live.
    return skill_dir / "evals" / "evals.yaml"


def load_cases(skill_dir):
    path = evals_path(skill_dir)
    return yaml.safe_load(path.read_text()) or []


def find_case(cases, case_id):
    for case in cases:
        if case["id"] == case_id:
            return case
    raise KeyError(case_id)


class OpencodeError(Exception):
    pass


def run_opencode(prompt, model):
    proc = subprocess.run(
        ["opencode", "run", "--format", "json", "--auto", "-m", model, prompt],
        capture_output=True,
        text=True,
    )
    # A failed opencode process says nothing about the skill, so it must not be
    # recorded as a graded FAIL.
    if proc.returncode != 0:
        raise OpencodeError(f"opencode exited {proc.returncode}: {proc.stderr.strip()}")
    events = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            events.append(json.loads(line))
    if not events:
        raise OpencodeError("opencode produced no JSON events")
    return events


def parse_events(events):
    text = []
    skills = []
    for event in events:
        part = event.get("part", {})
        if event.get("type") == "text":
            text.append(part.get("text", ""))
        if event.get("type") == "tool_use" and part.get("tool") == "skill":
            skills.append(part.get("state", {}).get("input", {}).get("id"))
    return {"output": "".join(text).strip(), "skills_loaded": skills}


def grade(checks, output):
    graded = []
    for check in checks:
        if check["type"] != "output_contains":
            raise ValueError(f"unsupported check type: {check['type']}")
        graded.append(
            {"type": check["type"], "value": check["value"], "passed": check["value"] in output}
        )
    return graded


def write_result(results_dir, record):
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    model = re.sub(r"[^A-Za-z0-9._-]+", "_", record["model"])
    name = f"{stamp}__{record['skill'].replace('/', '__')}__{record['case']}__{model}.json"
    path = results_dir / name
    path.write_text(json.dumps(record, indent=2) + "\n")
    return path
