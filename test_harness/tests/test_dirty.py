import json
import subprocess

import pytest
import yaml

from test_harness import cli, harness

MODEL = "github-copilot/claude-haiku-5.5"


def git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def make_repo(root):
    skill = root / "mod" / "skl"
    (skill / "evals").mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill\n")
    (skill / "evals" / "evals.yaml").write_text(yaml.safe_dump([{"id": "c", "prompt": "p", "checks": []}]))
    (root / "opencode.json").write_text("{}")
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return skill


@pytest.fixture
def fake_run(monkeypatch):
    monkeypatch.setattr(harness, "load_config", lambda path=None: {"models": [MODEL], "runs": 1})
    monkeypatch.setattr(harness, "export_session", lambda sid, cwd=None: None)
    calls = []

    def run_opencode(prompt, model, cwd=None):
        calls.append(cwd)
        return [{"type": "text", "part": {"text": "hi"}}]

    monkeypatch.setattr(harness, "run_opencode", run_opencode)
    return calls


def records(root):
    return [json.loads(path.read_text()) for path in (root / "test_harness" / "results").glob("*.json")]


def test_skill_is_clean_when_everything_is_committed(tmp_path):
    skill = make_repo(tmp_path)

    assert harness.skill_is_dirty(tmp_path, "mod/skl") is False


def test_skill_is_dirty_after_editing_its_skill_md(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "mod" / "skl" / "SKILL.md").write_text("# changed\n")

    assert harness.skill_is_dirty(tmp_path, "mod/skl") is True


def test_skill_is_dirty_with_an_untracked_fixture(tmp_path):
    make_repo(tmp_path)
    fixture = tmp_path / "mod" / "skl" / "evals" / "fixtures" / "c"
    fixture.mkdir(parents=True)
    (fixture / "new.txt").write_text("x")

    assert harness.skill_is_dirty(tmp_path, "mod/skl") is True


def test_edits_to_the_cases_file_do_not_make_the_skill_dirty(tmp_path):
    skill = make_repo(tmp_path)
    (skill / "evals" / "evals.yaml").write_text("- id: other\n")

    assert harness.skill_is_dirty(tmp_path, "mod/skl") is False


def test_edits_to_another_skill_do_not_make_this_one_dirty(tmp_path):
    make_repo(tmp_path)
    other = tmp_path / "mod" / "other"
    other.mkdir(parents=True)
    (other / "SKILL.md").write_text("# other\n")

    assert harness.skill_is_dirty(tmp_path, "mod/skl") is False


def test_dirty_skill_is_refused_without_allow_dirty(tmp_path, monkeypatch, fake_run):
    make_repo(tmp_path)
    (tmp_path / "mod" / "skl" / "SKILL.md").write_text("# changed\n")
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL]) == 2
    assert fake_run == []
    assert records(tmp_path) == []


def test_allow_dirty_runs_and_labels_the_records_working_tree(tmp_path, monkeypatch, fake_run):
    make_repo(tmp_path)
    (tmp_path / "mod" / "skl" / "SKILL.md").write_text("# changed\n")
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL, "--allow-dirty"]) == 0

    assert {record["label"] for record in records(tmp_path)} == {"working-tree"}


def test_clean_skill_records_have_no_label(tmp_path, monkeypatch, fake_run):
    make_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL]) == 0

    assert {record["label"] for record in records(tmp_path)} == {None}
