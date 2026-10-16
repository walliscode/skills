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

needs_opencode = pytest.mark.skipif(
    shutil.which("opencode") is None, reason="opencode is not on PATH"
)


@pytest.fixture
def project(tmp_path):
    """A temp copy of the fixture skill and opencode config, so runs never touch the repo's results."""
    shutil.copytree(REPO_ROOT / "harness-fixtures", tmp_path / "harness-fixtures")
    shutil.copy(REPO_ROOT / "opencode.json", tmp_path / "opencode.json")
    return tmp_path


def write_cases(project, cases):
    path = project / "harness-fixtures" / "canary-word" / "evals" / "evals.yaml"
    path.write_text(yaml.safe_dump(cases))


def run_harness(project, *, skill="harness-fixtures/canary-word", case="reports-canary-word", model=MODEL):
    # Pass model=None to leave out -m, which is how the required-flag test runs.
    args = [skill, "--case", case]
    if model is not None:
        args += ["-m", model]
    proc = subprocess.run(
        [sys.executable, "-m", "test_harness", *args],
        cwd=project,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
    )
    return proc


def only_result(project):
    files = list((project / "test_harness" / "results").glob("*.json"))
    assert len(files) == 1, files
    return json.loads(files[0].read_text())


@needs_opencode
def test_passes_when_skill_loads_and_output_contains_value(project):
    proc = run_harness(project)

    assert proc.returncode == 0, proc.stderr
    result = only_result(project)
    assert result["passed"] is True
    assert result["case"] == "reports-canary-word"
    assert result["skill"] == "harness-fixtures/canary-word"
    assert result["model"] == MODEL
    assert "ZEPHYR-7741" in result["output"]
    assert "canary-word" in result["skills_loaded"]
    assert result["checks"] == [{"type": "output_contains", "value": "ZEPHYR-7741", "passed": True}]


@needs_opencode
def test_fails_when_output_lacks_value(project):
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
    result = only_result(project)
    assert result["passed"] is False
    assert result["checks"] == [{"type": "output_contains", "value": "NOT-THE-WORD", "passed": False}]


@needs_opencode
def test_opencode_failure_is_an_error_not_a_fail(project):
    proc = run_harness(project, model="github-copilot/no-such-model")

    assert proc.returncode == 2
    assert "opencode exited" in proc.stderr
    assert not (project / "test_harness" / "results").exists()


def test_requires_model_flag(project):
    proc = run_harness(project, model=None)

    assert proc.returncode != 0
    assert not (project / "test_harness" / "results").exists()


def test_unknown_case_is_an_error(project):
    proc = run_harness(project, case="nope")

    assert proc.returncode == 2
    assert not (project / "test_harness" / "results").exists()
