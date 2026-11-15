import json
import subprocess

import yaml

from test_harness import cli, harness

MODEL = "github-copilot/claude-haiku-5.5"
OTHER_MODEL = "github-copilot/other-model"


def init_repo(root):
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    commit_all(root)


def commit_all(root):
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"], cwd=root, check=True)


def make_skill(root, skill, cases):
    skill_dir = root / skill
    (skill_dir / "evals").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(f"# {skill}\n")
    (skill_dir / "evals" / "evals.yaml").write_text(yaml.safe_dump(cases))


def write_batch(root, body):
    path = root / "batch.yaml"
    path.write_text(yaml.safe_dump(body))
    return path


def fake_opencode(monkeypatch):
    monkeypatch.setattr(
        harness, "run_opencode", lambda prompt, model, cwd=None: [{"type": "text", "part": {"text": "hi"}}]
    )


def records_in(root):
    return [json.loads(path.read_text()) for path in (root / "test_harness" / "results").glob("*.json")]


def project(tmp_path, monkeypatch):
    make_skill(tmp_path, "mod/one", [{"id": "a", "prompt": "p", "checks": []}, {"id": "b", "prompt": "p", "checks": []}])
    make_skill(tmp_path, "mod/two", [{"id": "c", "prompt": "p", "checks": []}])
    (tmp_path / "opencode.json").write_text("{}")
    init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    fake_opencode(monkeypatch)
    return tmp_path


def test_config_runs_every_skill_model_arm_and_case_it_lists(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    config = write_batch(
        root,
        {
            "skills": ["mod/one", "mod/two"],
            "models": [MODEL, OTHER_MODEL],
            "arms": ["with", "without"],
            "runs": 2,
        },
    )

    assert cli.main(["--config", str(config)]) == 0

    records = records_in(root)
    # 3 cases x 2 models x 2 arms x 2 runs.
    assert len(records) == 3 * 2 * 2 * 2
    assert {record["model"] for record in records} == {MODEL, OTHER_MODEL}
    assert {record["arm"] for record in records} == {"with", "without"}
    assert {record["n"] for record in records} == {2}
    assert {(record["skill"], record["case"]) for record in records} == {
        ("mod/one", "a"),
        ("mod/one", "b"),
        ("mod/two", "c"),
    }


def test_config_arms_limit_which_arms_run(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    config = write_batch(root, {"skills": ["mod/two"], "models": [MODEL], "arms": ["with"], "runs": 1})

    assert cli.main(["--config", str(config)]) == 0

    records = records_in(root)
    assert len(records) == 1
    assert records[0]["arm"] == "with"


def test_config_arms_default_to_both_arms(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    config = write_batch(root, {"skills": ["mod/two"], "models": [MODEL], "runs": 1})

    assert cli.main(["--config", str(config)]) == 0

    assert {record["arm"] for record in records_in(root)} == {"with", "without"}


def test_config_with_only_without_arm_exits_zero_even_when_runs_fail(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    make_skill(root, "mod/failing", [{"id": "f", "prompt": "p", "checks": [{"type": "output_contains", "value": "NOPE"}]}])
    commit_all(root)
    config = write_batch(root, {"skills": ["mod/failing"], "models": [MODEL], "arms": ["without"], "runs": 1})

    assert cli.main(["--config", str(config)]) == 0


def test_config_refuses_model_not_allowed_by_a_case_before_any_run(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    make_skill(root, "mod/pinned", [{"id": "p", "prompt": "p", "models": [OTHER_MODEL], "checks": []}])
    config = write_batch(root, {"skills": ["mod/two", "mod/pinned"], "models": [MODEL], "runs": 1})

    assert cli.main(["--config", str(config)]) == 2
    assert records_in(root) == []


def test_config_refuses_skill_missing_evals(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    config = write_batch(root, {"skills": ["mod/missing"], "models": [MODEL], "runs": 1})

    assert cli.main(["--config", str(config)]) == 2
    assert records_in(root) == []


def test_missing_config_file_is_a_usage_error(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)

    assert cli.main(["--config", str(root / "nope.yaml")]) == 2
    assert records_in(root) == []


def test_invalid_config_is_a_usage_error_and_runs_nothing(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    bad_bodies = [
        {"models": [MODEL], "runs": 1},
        {"skills": ["mod/two"], "runs": 1},
        {"skills": ["mod/two"], "models": [MODEL]},
        {"skills": ["mod/two"], "models": [MODEL], "runs": 0},
        {"skills": ["mod/two"], "models": [MODEL], "runs": 1, "arms": ["sideways"]},
        {"skills": ["mod/two"], "models": [MODEL], "runs": 1, "arms": []},
    ]
    for body in bad_bodies:
        config = write_batch(root, body)
        assert cli.main(["--config", str(config)]) == 2, body
    assert records_in(root) == []


def test_config_cannot_be_combined_with_model_flag(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    config = write_batch(root, {"skills": ["mod/two"], "models": [MODEL], "runs": 1})

    assert cli.main(["--config", str(config), "-m", MODEL]) == 2
    assert records_in(root) == []


def test_config_refuses_dirty_skill_unless_allowed(tmp_path, monkeypatch):
    root = project(tmp_path, monkeypatch)
    (root / "mod" / "two" / "SKILL.md").write_text("# edited\n")
    config = write_batch(root, {"skills": ["mod/two"], "models": [MODEL], "runs": 1})

    assert cli.main(["--config", str(config)]) == 2
    assert records_in(root) == []

    assert cli.main(["--config", str(config), "--allow-dirty"]) == 0
    assert {record["label"] for record in records_in(root)} == {"working-tree"}
