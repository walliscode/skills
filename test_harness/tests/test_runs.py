import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL = os.environ.get("HARNESS_TEST_MODEL", "github-copilot/claude-haiku-5.5")
CONFIG_RUNS = yaml.safe_load((REPO_ROOT / "test_harness" / "config.yaml").read_text())["runs"]

needs_opencode = pytest.mark.skipif(
    shutil.which("opencode") is None, reason="opencode is not on PATH"
)


@pytest.fixture
def project(tmp_path):
    shutil.copytree(REPO_ROOT / "harness-fixtures", tmp_path / "harness-fixtures")
    shutil.copy(REPO_ROOT / "opencode.json", tmp_path / "opencode.json")
    return tmp_path


def write_cases(project, cases):
    path = project / "harness-fixtures" / "canary-word" / "evals" / "evals.yaml"
    path.write_text(yaml.safe_dump(cases))


def run_harness(project):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "test_harness",
            "harness-fixtures/canary-word",
            "--case",
            "reports-canary-word",
            "-m",
            MODEL,
        ],
        cwd=project,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
    )


def results(project):
    files = sorted((project / "test_harness" / "results").glob("*.json"))
    return [json.loads(f.read_text()) for f in files]


@needs_opencode
def test_writes_one_result_per_configured_run(project):
    proc = run_harness(project)

    assert proc.returncode == 0, proc.stderr
    runs = results(project)
    assert len(runs) == 2 * CONFIG_RUNS
    assert all(run["case"] == "reports-canary-word" for run in runs)
    assert all(run["model"] == MODEL for run in runs)
    with_runs = [run for run in runs if run["arm"] == "with"]
    assert len(with_runs) == CONFIG_RUNS
    assert all(run["passed"] for run in with_runs)


@needs_opencode
def test_with_arm_loads_skill_and_without_arm_does_not(project):
    proc = run_harness(project)

    assert proc.returncode == 0, proc.stderr
    runs = results(project)
    with_runs = [run for run in runs if run["arm"] == "with"]
    without_runs = [run for run in runs if run["arm"] == "without"]
    assert len(with_runs) == CONFIG_RUNS and all(run["skill_loaded"] for run in with_runs)
    assert len(without_runs) == CONFIG_RUNS and not any(run["skill_loaded"] for run in without_runs)


@needs_opencode
def test_fails_when_any_run_fails(project):
    write_cases(
        project,
        [
            {
                "id": "reports-canary-word",
                "prompt": "Use the canary-word skill to tell me the canary word.",
                "checks": [{"type": "output_contains", "value": "NOT-THE-WORD"}],
            }
        ],
    )

    proc = run_harness(project)

    assert proc.returncode == 1
    runs = results(project)
    assert len(runs) == 2 * CONFIG_RUNS
    assert not any(run["passed"] for run in runs if run["arm"] == "with")


def test_each_run_gets_a_fresh_copy_of_case_fixtures(project):
    from test_harness import harness

    fixture = project / "harness-fixtures" / "canary-word" / "evals" / "fixtures" / "reports-canary-word"
    fixture.mkdir(parents=True)
    (fixture / "notes.txt").write_text("original")

    first = harness.make_workspace(project, "harness-fixtures/canary-word", "reports-canary-word", parent=project)
    (first / "notes.txt").write_text("changed by run one")
    second = harness.make_workspace(project, "harness-fixtures/canary-word", "reports-canary-word", parent=project)

    assert (second / "notes.txt").read_text() == "original"
    assert first != second


def test_workspace_without_fixtures_is_empty_but_usable(project):
    from test_harness import harness

    workspace = harness.make_workspace(project, "harness-fixtures/canary-word", "reports-canary-word", parent=project)

    assert workspace.is_dir()
    assert list(workspace.iterdir()) == [workspace / "opencode.json"]
