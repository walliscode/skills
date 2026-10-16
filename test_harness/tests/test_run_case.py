import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

FAKE_OPENCODE = """#!{python}
import os
import sys

with open(os.environ["FAKE_OPENCODE_ARGS"], "w") as f:
    f.write("\\n".join(sys.argv[1:]))
with open(os.environ["FAKE_OPENCODE_STDOUT"]) as f:
    sys.stdout.write(f.read())
"""


def jsonl(*events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


def skill_load(skill_id):
    return {
        "type": "tool_use",
        "sessionID": "ses_1",
        "part": {"tool": "skill", "state": {"input": {"id": skill_id}}},
    }


def text(value):
    return {"type": "text", "sessionID": "ses_1", "part": {"text": value}}


@pytest.fixture
def project(tmp_path):
    skill_dir = tmp_path / "engineering" / "greeter"
    (skill_dir / "evals").mkdir(parents=True)
    (skill_dir / "evals" / "evals.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "greets-ada",
                    "prompt": "Greet Ada.",
                    "checks": [{"type": "output_contains", "value": "Ada"}],
                }
            ]
        )
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "opencode"
    fake.write_text(FAKE_OPENCODE.format(python=sys.executable))
    fake.chmod(0o755)
    return tmp_path


def run_harness(project, stdout, *args):
    bin_dir = project / "bin"
    stdout_file = project / "stdout.jsonl"
    stdout_file.write_text(stdout)
    args_file = project / "opencode-args.txt"
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PYTHONPATH": str(REPO_ROOT),
        "FAKE_OPENCODE_STDOUT": str(stdout_file),
        "FAKE_OPENCODE_ARGS": str(args_file),
    }
    proc = subprocess.run(
        [sys.executable, "-m", "test_harness", *args],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc, args_file


def only_result(project):
    files = list((project / "test_harness" / "results").glob("*.json"))
    assert len(files) == 1, files
    return json.loads(files[0].read_text())


def test_passes_when_output_contains_value(project):
    stdout = jsonl(skill_load("greeter"), text("Hello Ada!"))

    proc, _ = run_harness(
        project, stdout, "engineering/greeter", "--case", "greets-ada", "-m", "provider/model-x"
    )

    assert proc.returncode == 0, proc.stderr
    result = only_result(project)
    assert result["passed"] is True
    assert result["case"] == "greets-ada"
    assert result["skill"] == "engineering/greeter"
    assert result["arm"] == "with"
    assert result["model"] == "provider/model-x"
    assert result["output"] == "Hello Ada!"
    assert result["checks"] == [{"type": "output_contains", "value": "Ada", "passed": True}]


def test_fails_when_output_lacks_value(project):
    stdout = jsonl(text("Hello stranger"))

    proc, _ = run_harness(
        project, stdout, "engineering/greeter", "--case", "greets-ada", "-m", "provider/model-x"
    )

    assert proc.returncode == 1
    result = only_result(project)
    assert result["passed"] is False
    assert result["checks"] == [{"type": "output_contains", "value": "Ada", "passed": False}]


def test_invokes_opencode_with_json_auto_and_model(project):
    stdout = jsonl(text("Ada"))

    proc, args_file = run_harness(
        project, stdout, "engineering/greeter", "--case", "greets-ada", "-m", "provider/model-x"
    )

    assert proc.returncode == 0, proc.stderr
    args = args_file.read_text().split("\n")
    assert args[:6] == ["run", "--format", "json", "--auto", "-m", "provider/model-x"]
    assert args[-1] == "Greet Ada."


def test_records_skills_loaded_from_tool_use_events(project):
    stdout = jsonl(skill_load("greeter"), text("Ada"))

    proc, _ = run_harness(
        project, stdout, "engineering/greeter", "--case", "greets-ada", "-m", "provider/model-x"
    )

    assert proc.returncode == 0, proc.stderr
    assert only_result(project)["skills_loaded"] == ["greeter"]


def test_requires_model_flag(project):
    proc, args_file = run_harness(
        project, jsonl(text("Ada")), "engineering/greeter", "--case", "greets-ada"
    )

    assert proc.returncode != 0
    assert not args_file.exists()
    assert not (project / "test_harness" / "results").exists()


def test_unknown_case_is_an_error(project):
    proc, args_file = run_harness(
        project, jsonl(text("Ada")), "engineering/greeter", "--case", "nope", "-m", "provider/model-x"
    )

    assert proc.returncode != 0
    assert not args_file.exists()
