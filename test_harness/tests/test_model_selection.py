import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_MODEL = "github-copilot/claude-haiku-5.5"
UNLISTED_MODEL = "github-copilot/not-in-the-list"

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


def run_harness(project, *, model=CONFIG_MODEL):
    args = ["harness-fixtures/canary-word", "--case", "reports-canary-word"]
    if model is not None:
        args += ["-m", model]
    return subprocess.run(
        [sys.executable, "-m", "test_harness", *args],
        cwd=project,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
    )


def case_with_models(models):
    return [
        {
            "id": "reports-canary-word",
            "prompt": "Use the canary-word skill to tell me the canary word.",
            "models": models,
            "checks": [{"type": "output_contains", "value": "ZEPHYR-7741"}],
        }
    ]


def test_refuses_model_not_in_config_list(project):
    proc = run_harness(project, model=UNLISTED_MODEL)

    assert proc.returncode == 2
    assert UNLISTED_MODEL in proc.stderr
    assert not (project / "test_harness" / "results").exists()


def test_case_models_override_config_list(project):
    write_cases(project, case_with_models([UNLISTED_MODEL]))

    proc = run_harness(project, model=CONFIG_MODEL)

    assert proc.returncode == 2
    assert UNLISTED_MODEL in proc.stderr
    assert not (project / "test_harness" / "results").exists()


@needs_opencode
def test_case_models_allow_model_outside_config_list(project):
    write_cases(project, case_with_models([UNLISTED_MODEL]))

    proc = run_harness(project, model=UNLISTED_MODEL)

    assert "opencode exited" in proc.stderr
