import pytest

from scripts.build_skill import BuildError, build_unit, is_fresh, main, write_skill


def make_repo(root):
    unit = root / "units" / "raii"
    (unit / "parts").mkdir(parents=True)
    (unit / "SKILL.md").write_text(
        "---\nname: raii\ndescription: RAII guidance.\n---\n\n"
        "@include units/raii/parts/intro.md\n\n"
        "@include units/raii/parts/rules.md\n"
    )
    (unit / "parts" / "intro.md").write_text("Intro text.\n")
    (unit / "parts" / "rules.md").write_text("Rule one.\nRule two.\n")
    return unit


def test_each_included_block_is_preceded_by_its_source_marker(tmp_path):
    unit = make_repo(tmp_path)

    built = build_unit(unit, tmp_path)

    assert built == (
        "---\nname: raii\ndescription: RAII guidance.\n---\n\n"
        "<!-- source: units/raii/parts/intro.md -->\n"
        "Intro text.\n\n"
        "<!-- source: units/raii/parts/rules.md -->\n"
        "Rule one.\nRule two.\n"
    )


def test_building_twice_gives_identical_output(tmp_path):
    unit = make_repo(tmp_path)

    assert build_unit(unit, tmp_path) == build_unit(unit, tmp_path)


def test_missing_include_fails_the_build(tmp_path):
    unit = make_repo(tmp_path)
    (unit / "parts" / "rules.md").unlink()

    with pytest.raises(BuildError, match="rules.md"):
        build_unit(unit, tmp_path)


def test_unit_without_skill_md_fails_the_build(tmp_path):
    unit = make_repo(tmp_path)
    (unit / "SKILL.md").unlink()

    with pytest.raises(BuildError, match="no SKILL.md"):
        build_unit(unit, tmp_path)


def test_cli_reports_missing_unit_as_error_not_traceback(tmp_path, capsys):
    make_repo(tmp_path)

    assert main(["--check", "--repo-root", str(tmp_path), "units/typo"]) == 1
    assert "error:" in capsys.readouterr().err


def test_write_skill_puts_output_under_skills_folder(tmp_path):
    unit = make_repo(tmp_path)

    write_skill(unit, tmp_path)

    out = tmp_path / "skills" / "raii" / "SKILL.md"
    assert out.read_text() == build_unit(unit, tmp_path)


def test_freshness_passes_when_committed_output_matches_build(tmp_path):
    unit = make_repo(tmp_path)
    write_skill(unit, tmp_path)

    assert is_fresh(unit, tmp_path)


def test_freshness_fails_when_committed_output_is_stale(tmp_path):
    unit = make_repo(tmp_path)
    write_skill(unit, tmp_path)
    (unit / "parts" / "intro.md").write_text("Changed intro.\n")

    assert not is_fresh(unit, tmp_path)


def test_freshness_fails_when_output_is_missing(tmp_path):
    unit = make_repo(tmp_path)

    assert not is_fresh(unit, tmp_path)


def test_cli_builds_each_unit_given(tmp_path):
    make_repo(tmp_path)

    assert main(["--repo-root", str(tmp_path), "units/raii"]) == 0
    assert (tmp_path / "skills" / "raii" / "SKILL.md").exists()


def test_cli_check_exits_nonzero_when_stale(tmp_path):
    unit = make_repo(tmp_path)
    write_skill(unit, tmp_path)
    (unit / "parts" / "intro.md").write_text("Changed intro.\n")

    assert main(["--check", "--repo-root", str(tmp_path), "units/raii"]) == 1
