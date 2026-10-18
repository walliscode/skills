"""@file harness.py
@brief Core logic for the skill eval harness: load cases, run opencode, grade, and store results.
"""

import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).with_name("config.yaml")


def load_config(path=CONFIG_PATH):
    """@brief Read the harness config file.

    @param path Path to the harness config YAML.
    @return The parsed config dict, with `models` (list of `provider/model`) and `runs` (int).
    """
    return yaml.safe_load(path.read_text())


def make_workspace(root, skill, case_id, parent=None):
    """@brief Build a fresh working directory for one run.

    Copies the case's fixtures from `<skill>/evals/fixtures/<case_id>/` if present, and
    writes the repo's `opencode.json` with its skill paths made absolute, so the skill
    under test still loads from the temp directory.

    @param root Repo root that `opencode.json` and the skill paths are relative to.
    @param skill The skill path, e.g. `engineering/tdd`.
    @param case_id The case id.
    @param parent Directory to create the workspace in, or None for the system temp directory.
    @return Path to a new temporary directory the caller should remove.
    """
    workspace = Path(tempfile.mkdtemp(prefix="harness-run-", dir=parent))
    fixtures = root / skill / "evals" / "fixtures" / case_id
    if fixtures.is_dir():
        shutil.copytree(fixtures, workspace, dirs_exist_ok=True)
    config = json.loads((root / "opencode.json").read_text())
    if "skills" in config:
        # Skill paths are relative to the repo root, but the workspace is a temp dir.
        config["skills"] = [str((root / entry).resolve()) for entry in config["skills"]]
    (workspace / "opencode.json").write_text(json.dumps(config, indent=2) + "\n")
    return workspace


def allowed_models(case, config_models):
    """@brief Return the models a case may run with.

    A case's own `models` field overrides the config list.

    @param case The case dict.
    @param config_models The models from the harness config.
    @return The list of allowed `provider/model` strings for the case.
    """
    return case["models"] if "models" in case else config_models


def evals_path(skill_dir):
    """@brief Return the path to a skill's eval cases file.

    The one place that knows where a skill's eval cases live.

    @param skill_dir Path to the skill directory, e.g. `engineering/tdd`.
    @return Path to `<skill_dir>/evals/evals.yaml`.
    """
    return skill_dir / "evals" / "evals.yaml"


def load_cases(skill_dir):
    """@brief Load the list of eval cases for a skill.

    @param skill_dir Path to the skill directory.
    @return The parsed YAML list of cases, or an empty list if the file is empty.
    """
    path = evals_path(skill_dir)
    return yaml.safe_load(path.read_text()) or []


def find_case(cases, case_id):
    """@brief Find a case by its `id` field.

    @param cases List of case dicts as returned by load_cases().
    @param case_id The `id` to look for.
    @return The matching case dict.
    @throws KeyError If no case has that id.
    """
    for case in cases:
        if case["id"] == case_id:
            return case
    raise KeyError(case_id)


class OpencodeError(Exception):
    """@brief Raised when the opencode process fails or produces no usable output."""


def run_opencode(prompt, model, cwd=None):
    """@brief Run one prompt through `opencode run` and return its JSONL events.

    A failed opencode process says nothing about the skill, so it is raised
    as an error rather than recorded as a graded FAIL.

    @param prompt The prompt text sent to opencode.
    @param model The `provider/model` string passed to `opencode -m`.
    @param cwd Directory to run opencode in, or None for the current directory.
    @return List of decoded JSON event dicts from stdout, in order.
    @throws OpencodeError If opencode exits non-zero or prints no JSON events.
    """
    proc = subprocess.run(
        ["opencode", "run", "--format", "json", "--auto", "-m", model, prompt],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
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
    """@brief Extract the final text and the skills loaded from opencode events.

    @param events List of event dicts from run_opencode().
    @return Dict with `output` (concatenated text parts, stripped) and
            `skills_loaded` (list of skill ids from `skill` tool_use events, in order).
    """
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
    """@brief Grade a run's output against a list of deterministic checks.

    @param checks List of check dicts, each with `type` and `value`.
    @param output The output text to grade.
    @return List of graded check dicts with `type`, `value` and `passed`.
    @throws ValueError If a check has an unsupported `type`.
    """
    graded = []
    for check in checks:
        if check["type"] != "output_contains":
            raise ValueError(f"unsupported check type: {check['type']}")
        graded.append(
            {"type": check["type"], "value": check["value"], "passed": check["value"] in output}
        )
    return graded


def build_record(skill, case_id, model, case, events):
    """@brief Turn one opencode run into the stored result record.

    Parses the events, grades them against the case's checks, and bundles the result.

    @param skill The skill path, e.g. `engineering/tdd`.
    @param case_id The case id.
    @param model The model string used for the run.
    @param case The case dict, including `prompt` and `checks`.
    @param events List of event dicts from run_opencode().
    @return The result record dict, ready for write_result().
    """
    parsed = parse_events(events)
    checks = grade(case.get("checks", []), parsed["output"])
    return {
        "skill": skill,
        "case": case_id,
        "model": model,
        "prompt": case["prompt"],
        "output": parsed["output"],
        "skills_loaded": parsed["skills_loaded"],
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
    }


def write_result(results_dir, record):
    """@brief Write one result record as a JSON file.

    Creates the directory if needed. The filename includes a UTC timestamp,
    the skill, the case and the model, so each run gets its own file.

    @param results_dir Directory to write into.
    @param record Result dict from build_record().
    @return Path to the written file.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    model = re.sub(r"[^A-Za-z0-9._-]+", "_", record["model"])
    name = f"{stamp}__{record['skill'].replace('/', '__')}__{record['case']}__{model}.json"
    path = results_dir / name
    path.write_text(json.dumps(record, indent=2) + "\n")
    return path
