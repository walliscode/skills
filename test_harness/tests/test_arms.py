import json

from test_harness import harness

SKILL = "harness-fixtures/canary-word"


def test_without_arm_denies_skill_under_test_in_workspace_config(tmp_path):
    root = tmp_path
    (root / "opencode.json").write_text(json.dumps({"skills": ["./harness-fixtures"]}))

    workspace = harness.make_workspace(root, SKILL, "reports-canary-word", parent=tmp_path, arm="without")

    config = json.loads((workspace / "opencode.json").read_text())
    assert config["permission"] == {"skill": {"canary-word": "deny"}}


def test_with_arm_leaves_skill_available_in_workspace_config(tmp_path):
    root = tmp_path
    (root / "opencode.json").write_text(json.dumps({"skills": ["./harness-fixtures"]}))

    workspace = harness.make_workspace(root, SKILL, "reports-canary-word", parent=tmp_path, arm="with")

    config = json.loads((workspace / "opencode.json").read_text())
    assert "permission" not in config


def test_record_names_its_arm():
    case = {"prompt": "p", "checks": []}
    record = harness.build_record(SKILL, "reports-canary-word", "m", case, [], arm="without")
    assert record["arm"] == "without"


def test_run_opencode_sets_pwd_to_its_working_directory(tmp_path, monkeypatch):
    captured = {}

    class Done:
        returncode = 0
        stdout = '{"type": "text", "part": {"text": "hi"}}\n'
        stderr = ""

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return Done()

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    monkeypatch.setenv("PWD", "/repo")

    harness.run_opencode("prompt", "m", cwd=tmp_path)

    assert captured["cwd"] == tmp_path
    assert captured["env"]["PWD"] == str(tmp_path)
