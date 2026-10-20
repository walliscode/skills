import json

import yaml

from test_harness import cli, harness

MODEL = "github-copilot/claude-haiku-5.5"


def test_cli_stores_skill_hash_and_n_in_every_run_record(tmp_path, monkeypatch):
    skill_dir = tmp_path / "mod" / "skl"
    (skill_dir / "evals").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# skill\n")
    (skill_dir / "evals" / "evals.yaml").write_text(yaml.safe_dump([{"id": "c", "prompt": "p", "checks": []}]))
    (tmp_path / "opencode.json").write_text("{}")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(harness, "load_config", lambda path=None: {"models": [MODEL], "runs": 2})
    monkeypatch.setattr(
        harness, "run_opencode", lambda prompt, model, cwd=None: [{"type": "text", "part": {"text": "hi"}}]
    )

    assert cli.main(["mod/skl", "--case", "c", "-m", MODEL]) == 0

    records = [json.loads(path.read_text()) for path in (tmp_path / "test_harness" / "results").glob("*.json")]
    assert len(records) == 4
    assert {record["skill_hash"] for record in records} == {harness.skill_hash(skill_dir)}
    assert {record["n"] for record in records} == {2}


def test_cli_records_failed_export_and_keeps_running_the_batch(tmp_path, monkeypatch):
    skill_dir = tmp_path / "mod" / "skl"
    (skill_dir / "evals").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# skill\n")
    (skill_dir / "evals" / "evals.yaml").write_text(yaml.safe_dump([{"id": "c", "prompt": "p", "checks": []}]))
    (tmp_path / "opencode.json").write_text("{}")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(harness, "load_config", lambda path=None: {"models": [MODEL], "runs": 3})
    monkeypatch.setattr(
        harness, "run_opencode", lambda prompt, model, cwd=None: [{"type": "text", "part": {"text": "hi"}}]
    )
    exports = iter(["ok", "fail", "ok", "ok", "ok", "ok"])

    def fake_export(sid, cwd=None):
        if next(exports) == "fail":
            raise harness.ExportError("boom")
        return {"info": {"cost": 0.5, "tokens": {"input": 1, "output": 2, "cache": {"read": 3}}}}

    monkeypatch.setattr(harness, "export_session", fake_export)

    assert cli.main(["mod/skl", "--case", "c", "-m", MODEL]) == 2

    records = [json.loads(path.read_text()) for path in (tmp_path / "test_harness" / "results").glob("*.json")]
    assert len(records) == 6
    failed = [record for record in records if record["export_error"] is not None]
    assert len(failed) == 1
    assert failed[0]["export_error"] == "boom"
    assert failed[0]["cost"] is None
    assert failed[0]["tokens"] == {"input": None, "output": None, "cached": None}
    succeeded = [record for record in records if record["export_error"] is None]
    assert {record["cost"] for record in succeeded} == {0.5}
