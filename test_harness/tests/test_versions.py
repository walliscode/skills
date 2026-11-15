import json
import subprocess

import yaml

from test_harness import cli, harness

MODEL = "github-copilot/claude-haiku-5.5"


def git(root, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root, check=True, capture_output=True)


def make_skill(root, skill, body):
    skill_dir = root / skill
    (skill_dir / "evals").mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body)
    (skill_dir / "evals" / "evals.yaml").write_text(yaml.safe_dump([{"id": "c", "prompt": "p", "checks": []}]))


def project(tmp_path, monkeypatch):
    make_skill(tmp_path, "mod/skl", "# version one\n")
    (tmp_path / "opencode.json").write_text("{}")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "init")
    git(tmp_path, "tag", "skl-v0.1")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        harness, "run_opencode", lambda prompt, model, cwd=None: [{"type": "text", "part": {"text": "hi"}}]
    )
    return tmp_path


def records_in(root):
    return [json.loads(path.read_text()) for path in (root / "test_harness" / "results").glob("*.json")]


def test_version_reads_the_skill_from_its_tag_not_the_working_tree(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    tagged_hash = harness.skill_hash(root / "mod" / "skl")
    make_skill(root, "mod/skl", "# version two\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "edit")

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL, "--version", "0.1"]) == 0

    records = records_in(root)
    assert records
    assert {record["skill_hash"] for record in records} == {tagged_hash}
    assert {record["tag"] for record in records} == {"skl-v0.1"}


def test_version_run_ignores_uncommitted_edits_and_is_not_labelled_working_tree(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    (root / "mod" / "skl" / "SKILL.md").write_text("# uncommitted\n")

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL, "--version", "0.1"]) == 0

    records = records_in(root)
    assert {record["label"] for record in records} == {None}
    assert {record["tag"] for record in records} == {"skl-v0.1"}


def test_version_removes_its_worktree_afterwards(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL, "--version", "0.1"]) == 0

    listing = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=root, capture_output=True, text=True, check=True)
    assert listing.stdout.count("worktree ") == 1


def test_version_removes_its_worktree_when_the_run_errors(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)

    def broken(prompt, model, cwd=None):
        raise harness.OpencodeError("boom")

    monkeypatch.setattr(harness, "run_opencode", broken)

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL, "--version", "0.1"]) == 2

    listing = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=root, capture_output=True, text=True, check=True)
    assert listing.stdout.count("worktree ") == 1


def test_missing_tag_is_a_usage_error_and_runs_nothing(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL, "--version", "9.9"]) == 2
    assert records_in(root) == []


def test_version_needs_skill_and_model(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)

    assert cli.main(["-m", MODEL, "--version", "0.1"]) == 2
    assert records_in(root) == []


def test_skill_records_carry_null_tag_for_plain_runs(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL]) == 0

    assert {record["tag"] for record in records_in(root)} == {None}


def test_skills_root_reads_skills_from_the_given_folder(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    elsewhere = tmp_path / "elsewhere"
    make_skill(elsewhere, "mod/skl", "# elsewhere\n")
    (elsewhere / "opencode.json").write_text("{}")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "elsewhere")
    expected = harness.skill_hash(elsewhere / "mod" / "skl")

    assert cli.main(["--skill", "mod/skl", "--case", "c", "-m", MODEL, "--skills-root", str(elsewhere)]) == 0

    assert {record["skill_hash"] for record in records_in(root)} == {expected}


def test_version_cannot_be_combined_with_skills_root(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)

    assert cli.main(["--skill", "mod/skl", "-m", MODEL, "--version", "0.1", "--skills-root", str(root)]) == 2
    assert records_in(root) == []


def test_version_cannot_be_combined_with_config(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    config = root / "batch.yaml"
    config.write_text(yaml.safe_dump({"skills": ["mod/skl"], "models": [MODEL], "runs": 1}))

    assert cli.main(["--config", str(config), "--version", "0.1"]) == 2
    assert records_in(root) == []
