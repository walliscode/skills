from test_harness import harness

CASE = {"id": "c", "prompt": "p", "checks": []}


def make_skill(root, skill_text="# skill\n", fixture_text="start\n"):
    skill_dir = root / "mod" / "skl"
    (skill_dir / "evals" / "fixtures" / "c").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(skill_text)
    (skill_dir / "evals" / "fixtures" / "c" / "notes.txt").write_text(fixture_text)
    return skill_dir


def test_hash_is_the_same_when_nothing_changes(tmp_path):
    skill_dir = make_skill(tmp_path)

    assert harness.skill_hash(skill_dir) == harness.skill_hash(skill_dir)


def test_hash_changes_when_skill_md_changes(tmp_path):
    skill_dir = make_skill(tmp_path)
    before = harness.skill_hash(skill_dir)

    (skill_dir / "SKILL.md").write_text("# skill, edited\n")

    assert harness.skill_hash(skill_dir) != before


def test_hash_changes_when_a_fixture_changes(tmp_path):
    skill_dir = make_skill(tmp_path)
    before = harness.skill_hash(skill_dir)

    (skill_dir / "evals" / "fixtures" / "c" / "notes.txt").write_text("changed\n")

    assert harness.skill_hash(skill_dir) != before


def test_hash_ignores_the_eval_cases_file(tmp_path):
    skill_dir = make_skill(tmp_path)
    before = harness.skill_hash(skill_dir)

    (skill_dir / "evals" / "evals.yaml").write_text("- id: c\n")

    assert harness.skill_hash(skill_dir) == before


def test_hash_works_for_a_skill_folder_with_no_skill_md(tmp_path):
    skill_dir = tmp_path / "mod" / "skl"
    (skill_dir / "evals").mkdir(parents=True)

    assert len(harness.skill_hash(skill_dir)) == 64


def test_record_includes_skill_hash_and_n():
    record = harness.build_record(
        "mod/skl", "c", "m", CASE, [], skill_hash="abc123", n=3
    )

    assert record["skill_hash"] == "abc123"
    assert record["n"] == 3
