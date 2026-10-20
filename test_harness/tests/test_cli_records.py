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
