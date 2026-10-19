import json

import yaml

from test_harness import cli, harness

MODEL = "github-copilot/claude-haiku-5.5"


def make_skill(root, skill, case_id):
    evals = root / skill / "evals"
    evals.mkdir(parents=True)
    (evals / "evals.yaml").write_text(
        yaml.safe_dump([{"id": case_id, "prompt": "p", "checks": []}])
    )


def make_project(root):
    (root / "opencode.json").write_text(json.dumps({"skills": []}))
    (root / "test_harness").mkdir()
    (root / "test_harness" / "config.yaml").write_text(
        yaml.safe_dump({"models": [MODEL], "runs": 1})
    )


def results_skills(root):
    files = sorted((root / "test_harness" / "results").glob("*.json"))
    return sorted({json.loads(f.read_text())["skill"] for f in files})


def fake_opencode(monkeypatch):
    monkeypatch.setattr(
        harness, "run_opencode", lambda prompt, model, cwd=None: [{"type": "text", "part": {"text": "ok"}}]
    )


def test_discover_finds_every_skill_with_evals(tmp_path):
    make_skill(tmp_path, "tools/alpha", "a1")
    make_skill(tmp_path, "tools/beta", "b1")
    (tmp_path / "tools" / "gamma").mkdir(parents=True)
    (tmp_path / "tools" / "gamma" / "SKILL.md").write_text("no evals here")

    assert harness.discover_skills(tmp_path) == ["tools/alpha", "tools/beta"]


def test_no_skill_argument_runs_every_skill(tmp_path, monkeypatch):
    make_project(tmp_path)
    make_skill(tmp_path, "tools/alpha", "a1")
    make_skill(tmp_path, "tools/beta", "b1")
    monkeypatch.chdir(tmp_path)
    fake_opencode(monkeypatch)

    assert cli.main(["-m", MODEL]) == 0
    assert results_skills(tmp_path) == ["tools/alpha", "tools/beta"]


def test_skill_argument_runs_only_that_skill(tmp_path, monkeypatch):
    make_project(tmp_path)
    make_skill(tmp_path, "tools/alpha", "a1")
    make_skill(tmp_path, "tools/beta", "b1")
    monkeypatch.chdir(tmp_path)
    fake_opencode(monkeypatch)

    assert cli.main(["tools/alpha", "-m", MODEL]) == 0
    assert results_skills(tmp_path) == ["tools/alpha"]


def test_case_without_skill_runs_only_skills_that_have_it(tmp_path, monkeypatch):
    make_project(tmp_path)
    make_skill(tmp_path, "tools/alpha", "a1")
    make_skill(tmp_path, "tools/beta", "b1")
    monkeypatch.chdir(tmp_path)
    fake_opencode(monkeypatch)

    assert cli.main(["--case", "a1", "-m", MODEL]) == 0
    assert results_skills(tmp_path) == ["tools/alpha"]
