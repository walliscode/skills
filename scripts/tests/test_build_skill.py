import pytest

from scripts.build_skill import BuildError, build_skill, is_fresh, main, write_skill


def make_repo(root):
    (root / "units").mkdir()
    (root / "units" / "intro.md").write_text("Intro text.\n")
    (root / "units" / "rules.md").write_text("Rule one.\nRule two.\n")
    skill = root / "skills" / "raii"
    skill.mkdir(parents=True)
    (skill / "skill.yaml").write_text(
        "name: raii\n"
        "description: RAII guidance.\n"
        "units:\n"
        "  - units/intro.md\n"
        "  - units/rules.md\n"
    )
    return skill / "skill.yaml"


def test_each_unit_is_preceded_by_its_source_marker_in_order(tmp_path):
    spec = make_repo(tmp_path)

    assert build_skill(spec, tmp_path) == (
        "---\nname: raii\ndescription: RAII guidance.\n---\n\n"
        "<!-- source: units/intro.md -->\n"
        "Intro text.\n\n"
        "<!-- source: units/rules.md -->\n"
        "Rule one.\nRule two.\n"
    )


def test_building_twice_gives_identical_output(tmp_path):
    spec = make_repo(tmp_path)

    assert build_skill(spec, tmp_path) == build_skill(spec, tmp_path)


def test_missing_unit_fails_the_build(tmp_path):
    spec = make_repo(tmp_path)
    (tmp_path / "units" / "rules.md").unlink()

    with pytest.raises(BuildError, match="units/rules.md"):
        build_skill(spec, tmp_path)


def test_spec_without_units_fails_the_build(tmp_path):
    spec = make_repo(tmp_path)
    spec.write_text("name: raii\ndescription: RAII guidance.\n")

    with pytest.raises(BuildError, match="units"):
        build_skill(spec, tmp_path)


def test_write_skill_puts_output_next_to_its_spec(tmp_path):
    spec = make_repo(tmp_path)

    write_skill(spec, tmp_path)

    out = tmp_path / "skills" / "raii" / "SKILL.md"
    assert out.read_text() == build_skill(spec, tmp_path)


def test_freshness_passes_when_committed_output_matches_build(tmp_path):
    spec = make_repo(tmp_path)
    write_skill(spec, tmp_path)

    assert is_fresh(spec, tmp_path)


def make_stale_repo(root):
    spec = make_repo(root)
    write_skill(spec, root)
    (root / "units" / "intro.md").write_text("Changed intro.\n")
    return spec


def test_freshness_fails_when_a_unit_changed(tmp_path):
    spec = make_stale_repo(tmp_path)

    assert not is_fresh(spec, tmp_path)


def test_freshness_fails_when_output_is_missing(tmp_path):
    spec = make_repo(tmp_path)

    assert not is_fresh(spec, tmp_path)


def test_cli_builds_each_skill_spec_given(tmp_path):
    make_repo(tmp_path)

    assert main(["--repo-root", str(tmp_path), "skills/raii/skill.yaml"]) == 0
    assert (tmp_path / "skills" / "raii" / "SKILL.md").exists()


def test_cli_check_exits_nonzero_when_stale(tmp_path):
    make_stale_repo(tmp_path)

    assert main(["--check", "--repo-root", str(tmp_path), "skills/raii/skill.yaml"]) == 1


def test_cli_reports_missing_spec_as_error_not_traceback(tmp_path, capsys):
    make_repo(tmp_path)

    assert main(["--check", "--repo-root", str(tmp_path), "skills/typo/skill.yaml"]) == 1
    assert "error:" in capsys.readouterr().err
