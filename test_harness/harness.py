"""@file harness.py
@brief Core logic for the skill eval harness: load cases, run opencode, grade, and store results.
"""

# Standard library imports: JSON, env vars, regexes, file copying, subprocesses,
# temp directories, timestamps and paths.
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Third-party YAML parser, used for the config and the eval case files.
import yaml

# The config file sits next to this module, so it is found wherever the harness is run from.
CONFIG_PATH = Path(__file__).with_name("config.yaml")


def load_config(path=CONFIG_PATH):
    """@brief Read the harness config file.

    @param path Path to the harness config YAML.
    @return The parsed config dict, with `models` (list of `provider/model`) and `runs` (int).
    """
    # Read the file as text, then parse the YAML into a dict.
    return yaml.safe_load(path.read_text())


def make_workspace(root, skill, case_id, parent=None, arm="with"):
    """@brief Build a fresh working directory for one run.

    Copies the case's fixtures from `<skill>/evals/fixtures/<case_id>/` if present, and
    writes the repo's `opencode.json` with its skill paths made absolute, so the skill
    under test still loads from the temp directory. The without arm also denies the
    skill under test, so the model cannot load it.

    @param root Repo root that `opencode.json` and the skill paths are relative to.
    @param skill The skill path, e.g. `engineering/tdd`.
    @param case_id The case id.
    @param parent Directory to create the workspace in, or None for the system temp directory.
    @param arm `with` to leave the skill available, `without` to deny it.
    @return Path to a new temporary directory the caller should remove.
    """
    # Create an empty temp directory for this run only. The prefix makes it easy to spot.
    workspace = Path(tempfile.mkdtemp(prefix="harness-run-", dir=parent))
    # Where this case's starting files live, if the case has any.
    fixtures = root / skill / "evals" / "fixtures" / case_id
    if fixtures.is_dir():
        # Copy the fixtures in. dirs_exist_ok lets this work even if the directory already exists.
        shutil.copytree(fixtures, workspace, dirs_exist_ok=True)
    # Load the repo's opencode.json as a dict so we can change it for this run.
    config = json.loads((root / "opencode.json").read_text())
    if "skills" in config:
        # Skill paths are relative to the repo root, but the workspace is a temp dir.
        # Turn each one into an absolute path so opencode can still find the skill.
        config["skills"] = [str((root / entry).resolve()) for entry in config["skills"]]
    if arm == "without":
        # The skill's id is its folder name, e.g. `engineering/tdd` -> `tdd`.
        skill_id = skill.rsplit("/", 1)[-1]
        # Deny that one skill for this run. Other skills are unaffected.
        config["permission"] = {"skill": {skill_id: "deny"}}
    # Write the adjusted config into the workspace, where opencode will read it.
    (workspace / "opencode.json").write_text(json.dumps(config, indent=2) + "\n")
    return workspace


def allowed_models(case, config_models):
    """@brief Return the models a case may run with.

    A case's own `models` field overrides the config list.

    @param case The case dict.
    @param config_models The models from the harness config.
    @return The list of allowed `provider/model` strings for the case.
    """
    # Use the case's own list if it set one, otherwise fall back to the config list.
    return case["models"] if "models" in case else config_models


def evals_path(skill_dir):
    """@brief Return the path to a skill's eval cases file.

    The one place that knows where a skill's eval cases live.

    @param skill_dir Path to the skill directory, e.g. `engineering/tdd`.
    @return Path to `<skill_dir>/evals/evals.yaml`.
    """
    # Build the path to evals.yaml inside the skill's evals folder.
    return skill_dir / "evals" / "evals.yaml"


def skill_hash(skill_dir):
    """@brief Hash a skill's content, so a change to it starts a new run group.

    Covers `SKILL.md` and every file under `evals/fixtures/`. The eval cases file is left out,
    since editing a case's checks does not change what the skill does.

    @param skill_dir Path to the skill directory, e.g. `engineering/tdd`.
    @return Hex SHA-256 digest of the skill's files, with their relative paths.
    """
    files = [skill_dir / "SKILL.md"] if (skill_dir / "SKILL.md").is_file() else []
    fixtures = skill_dir / "evals" / "fixtures"
    if fixtures.is_dir():
        files += sorted(path for path in fixtures.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    for path in files:
        # The path goes in too, so moving a file changes the hash even if its bytes don't.
        digest.update(path.relative_to(skill_dir).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def discover_skills(root):
    """@brief Find every skill under the repo root that has an eval cases file.

    Skills use the `<module>/<skill>` layout, so each one is two folders deep.

    @param root Repo root to search.
    @return Sorted list of `<module>/<skill>` paths, relative to root.
    """
    # Each evals.yaml sits at <module>/<skill>/evals/evals.yaml, so its skill folder is two levels above the file.
    return sorted(
        path.parent.parent.relative_to(root).as_posix() for path in root.glob("*/*/evals/evals.yaml")
    )


def load_cases(skill_dir):
    """@brief Load the list of eval cases for a skill.

    @param skill_dir Path to the skill directory.
    @return The parsed YAML list of cases, or an empty list if the file is empty.
    """
    path = evals_path(skill_dir)
    # An empty YAML file parses to None, so `or []` turns that into an empty list.
    return yaml.safe_load(path.read_text()) or []


def find_case(cases, case_id):
    """@brief Find a case by its `id` field.

    @param cases List of case dicts as returned by load_cases().
    @param case_id The `id` to look for.
    @return The matching case dict.
    @throws KeyError If no case has that id.
    """
    # Return the first case whose id matches.
    for case in cases:
        if case["id"] == case_id:
            return case
    # No match: raise so the caller can report the bad id.
    raise KeyError(case_id)


class OpencodeError(Exception):
    """@brief Raised when the opencode process fails or produces no usable output."""


class ExportError(Exception):
    """@brief Raised when a session export cannot be fetched or parsed. The message says why."""


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
    # opencode finds its project from PWD, which subprocess's cwd does not update.
    proc = subprocess.run(
        # The command: JSON output, auto-approve tool use, pick the model, then the prompt.
        ["opencode", "run", "--format", "json", "--auto", "-m", model, prompt],
        # Capture stdout and stderr as text instead of printing them.
        capture_output=True,
        text=True,
        # Run inside the workspace, if one was given.
        cwd=cwd,
        # Set PWD to match cwd, so opencode reads the workspace's opencode.json.
        # With no cwd, leave the environment alone (None).
        env={**os.environ, "PWD": str(cwd)} if cwd is not None else None,
    )
    # A non-zero exit means opencode itself failed, not that the skill failed.
    if proc.returncode != 0:
        raise OpencodeError(f"opencode exited {proc.returncode}: {proc.stderr.strip()}")
    events = []
    # Each line of stdout is one JSON event. Skip anything that isn't a JSON object.
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            events.append(json.loads(line))
    # No events at all means there is nothing to grade.
    if not events:
        raise OpencodeError("opencode produced no JSON events")
    return events


def session_id(events):
    """@brief Return the opencode session id that the run's events belong to.

    @param events List of event dicts from run_opencode().
    @return The first `sessionID` found in the events, or None if none has one.
    """
    for event in events:
        if event.get("sessionID"):
            return event["sessionID"]
    return None


def export_session(sid, cwd=None):
    """@brief Export one opencode session as JSON.

    @param sid The session id from session_id().
    @param cwd Directory to run opencode in, or None for the current directory.
    @return The parsed export dict, or None if there is no session id.
    @throws ExportError If opencode cannot be run, exits non-zero, or prints something that is not JSON.
    """
    if sid is None:
        return None
    try:
        proc = subprocess.run(
            ["opencode", "session", "export", sid],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
    except OSError as err:
        raise ExportError(str(err)) from err
    if proc.returncode != 0:
        raise ExportError(proc.stderr.strip() or f"opencode session export exited {proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as err:
        raise ExportError(f"session export was not valid JSON: {err}") from err


def session_usage(export):
    """@brief Pull the cost and token counts out of a session export.

    Any field the export lacks is None, so a missing export still gives a record of the same shape.

    @param export The dict from export_session(), or None.
    @return Dict with `cost` and `tokens` (`input`, `output`, `cached`, where cached is cache reads).
    """
    info = (export or {}).get("info", {})
    tokens = info.get("tokens") or {}
    cache = tokens.get("cache") or {}
    return {
        "cost": info.get("cost"),
        "tokens": {
            "input": tokens.get("input"),
            "output": tokens.get("output"),
            "cached": cache.get("read"),
        },
    }


def parse_events(events):
    """@brief Extract the final text and the skills loaded from opencode events.

    A skill counts as loaded only when its `skill` tool_use completed; denied or
    failed calls are not loads.

    @param events List of event dicts from run_opencode().
    @return Dict with `output` (concatenated text parts, stripped) and
            `skills_loaded` (list of skill ids from completed `skill` tool_use events, in order).
    """
    # Collected pieces of the model's reply, and the skill ids that really loaded.
    text = []
    skills = []
    for event in events:
        # The payload of each event lives under `part`; default to empty if missing.
        part = event.get("part", {})
        if event.get("type") == "text":
            # Keep the text of each reply piece, in order.
            text.append(part.get("text", ""))
        if event.get("type") == "tool_use" and part.get("tool") == "skill":
            # The state holds the status and input of this skill call.
            state = part.get("state", {})
            # Only a completed call counts as a load. Denied or errored calls are ignored.
            if state.get("status") == "completed":
                skills.append(state.get("input", {}).get("id"))
    # Join the text pieces into one string and remove surrounding whitespace.
    return {"output": "".join(text).strip(), "skills_loaded": skills}


def grade(checks, output, workspace=None):
    """@brief Grade a run's output and workspace files against a list of deterministic checks.

    @param checks List of check dicts, each with `type` and `value`. `file_contains`
           checks also have `path`, relative to the workspace.
    @param output The output text to grade.
    @param workspace Directory the run worked in, read by `file_contains` checks.
    @return List of graded check dicts: each check's fields plus `passed`.
    @throws ValueError If a check has an unsupported `type`.
    """
    graded = []
    for check in checks:
        if check["type"] == "output_contains":
            # Pass if the expected text appears anywhere in the output.
            passed = check["value"] in output
        elif check["type"] == "regex":
            # Pass if the pattern matches somewhere in the output.
            passed = re.search(check["value"], output) is not None
        elif check["type"] == "file_contains":
            # Build the file's path inside the workspace, or None if there is no workspace.
            target = workspace / check["path"] if workspace is not None else None
            # Pass only if the file exists and contains the expected text.
            passed = target is not None and target.is_file() and check["value"] in target.read_text(encoding="utf-8")
        else:
            # Unknown check types are a mistake in the case file, so fail loudly.
            raise ValueError(f"unsupported check type: {check['type']}")
        # Keep the check's own fields and add the result.
        graded.append({**check, "passed": passed})
    return graded


def grade_rubric(criteria, output, model):
    """@brief Ask the model whether an output meets a rubric's criteria.

    The reply counts as a pass only if it is exactly PASS, ignoring case and whitespace.
    Anything else, including a hedged reply, is a fail.

    @param criteria The rubric text describing what a passing answer looks like.
    @param output The run's output text to grade.
    @param model The `provider/model` string used to grade.
    @return True if the grader replied PASS, otherwise False.
    """
    prompt = (
        "You are grading an answer against criteria.\n\n"
        f"Criteria: {criteria}\n\n"
        f"Answer:\n{output}\n\n"
        "Reply with exactly PASS if the answer meets the criteria, otherwise reply with exactly FAIL. "
        "Reply with nothing else."
    )
    # Grade in an empty directory so the grader doesn't pick up the repo's skills or files.
    with tempfile.TemporaryDirectory(prefix="harness-judge-") as tmp:
        events = run_opencode(prompt, model, cwd=Path(tmp))
    return parse_events(events)["output"].strip().upper() == "PASS"


def build_record(
    skill,
    case_id,
    model,
    case,
    events,
    arm="with",
    workspace=None,
    judge=None,
    session=None,
    skill_hash=None,
    n=None,
    export_error=None,
):
    """@brief Turn one opencode run into the stored result record.

    Parses the events, grades them against the case's checks, runs the rubric if the checks passed, and bundles the result.

    @param skill The skill path, e.g. `engineering/tdd`.
    @param case_id The case id.
    @param model The model string used for the run.
    @param case The case dict, including `prompt` and `checks`.
    @param events List of event dicts from run_opencode().
    @param arm `with` or `without`, the arm the run was made under.
    @param workspace Directory the run worked in, for `file_contains` checks.
    @param judge Callable `(criteria, output) -> bool` used for the rubric, or None to skip it.
    @param session The dict from export_session() for this run, or None if it is unavailable.
    @param skill_hash The hash from skill_hash() at run time, or None if not known.
    @param n The `runs` value from the config this run was part of, or None if not known.
    @param export_error The message from the failed session export, or None if the export worked.
    @return The result record dict, ready for write_result().
    """
    # Pull out the reply text and the skills that loaded.
    parsed = parse_events(events)
    # Grade the reply and any workspace files. A case with no checks gets an empty list.
    checks = grade(case.get("checks", []), parsed["output"], workspace)
    checks_passed = all(check["passed"] for check in checks)
    # The rubric only runs once the cheap checks have passed, to save grading cost.
    rubric = None
    if checks_passed and judge is not None and case.get("rubric"):
        rubric = {"criteria": case["rubric"], "passed": judge(case["rubric"], parsed["output"])}
    # The skill's id is its folder name, the same form the skill tool uses.
    skill_id = skill.rsplit("/", 1)[-1]
    usage = session_usage(session)
    return {
        "skill": skill,
        "skill_hash": skill_hash,
        "n": n,
        "case": case_id,
        "model": model,
        "arm": arm,
        "session_id": session_id(events),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cost": usage["cost"],
        "tokens": usage["tokens"],
        "export_error": export_error,
        "prompt": case["prompt"],
        "output": parsed["output"],
        "skills_loaded": parsed["skills_loaded"],
        # Whether the skill under test was among the loaded skills.
        "skill_loaded": skill_id in parsed["skills_loaded"],
        "checks": checks,
        # Null when the rubric did not run.
        "rubric": rubric,
        # A run passes only if every check passed and the rubric, if run, passed.
        "passed": checks_passed and (rubric is None or rubric["passed"]),
    }


def write_result(results_dir, record):
    """@brief Write one result record as a JSON file.

    Creates the directory if needed. The filename includes a UTC timestamp,
    the skill, the case and the model, so each run gets its own file.

    @param results_dir Directory to write into.
    @param record Result dict from build_record().
    @return Path to the written file.
    """
    # Make sure the results folder exists.
    results_dir.mkdir(parents=True, exist_ok=True)
    # A UTC timestamp to microseconds, so files sort in run order and don't collide.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    # Replace anything unsafe in a filename (like `/` in `provider/model`) with `_`.
    model = re.sub(r"[^A-Za-z0-9._-]+", "_", record["model"])
    # Join the parts into one filename. `/` in the skill path becomes `__`.
    name = f"{stamp}__{record['skill'].replace('/', '__')}__{record['case']}__{record['arm']}__{model}.json"
    path = results_dir / name
    # Write the record as pretty JSON with a trailing newline.
    path.write_text(json.dumps(record, indent=2) + "\n")
    return path
