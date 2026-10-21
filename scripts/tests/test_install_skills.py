from scripts.install_skills import MARKER, install, main


def make_built_skill(repo_root, name, body="Built body.\n"):
    folder = repo_root / "skills" / name
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text(f"---\nname: {name}\n---\n{body}")
    return folder


def test_copies_every_built_skill_to_destination(tmp_path):
    src = tmp_path / "repo"
    make_built_skill(src, "raii")
    make_built_skill(src, "testing")
    dest = tmp_path / "user-skills"

    install(src, dest)

    assert (dest / "raii" / "SKILL.md").read_text() == "---\nname: raii\n---\nBuilt body.\n"
    assert (dest / "testing" / "SKILL.md").exists()


def test_reports_installed_for_new_skills(tmp_path):
    src = tmp_path / "repo"
    make_built_skill(src, "raii")

    assert install(src, tmp_path / "user-skills") == {"raii": "installed"}


def test_leaves_folder_it_did_not_install_untouched(tmp_path):
    src = tmp_path / "repo"
    make_built_skill(src, "raii")
    dest = tmp_path / "user-skills"
    foreign = dest / "raii"
    foreign.mkdir(parents=True)
    (foreign / "SKILL.md").write_text("mine\n")

    report = install(src, dest)

    assert (foreign / "SKILL.md").read_text() == "mine\n"
    assert report == {"raii": "skipped: not installed by this script"}


def test_rerun_after_source_change_updates_installed_skill(tmp_path):
    src = tmp_path / "repo"
    folder = make_built_skill(src, "raii")
    dest = tmp_path / "user-skills"
    install(src, dest)
    (folder / "SKILL.md").write_text("---\nname: raii\n---\nNew body.\n")

    report = install(src, dest)

    assert (dest / "raii" / "SKILL.md").read_text() == "---\nname: raii\n---\nNew body.\n"
    assert report == {"raii": "updated"}


def test_installed_folder_is_marked_so_later_runs_can_update_it(tmp_path):
    src = tmp_path / "repo"
    make_built_skill(src, "raii")
    dest = tmp_path / "user-skills"

    install(src, dest)

    assert (dest / "raii" / MARKER).exists()


def test_skill_folder_without_built_output_is_ignored(tmp_path):
    src = tmp_path / "repo"
    (src / "skills" / "unbuilt").mkdir(parents=True)
    (src / "skills" / "unbuilt" / "skill.yaml").write_text("name: unbuilt\n")

    assert install(src, tmp_path / "user-skills") == {}


def test_cli_installs_into_given_destination(tmp_path, capsys):
    src = tmp_path / "repo"
    make_built_skill(src, "raii")
    dest = tmp_path / "user-skills"

    assert main(["--repo-root", str(src), "--dest", str(dest)]) == 0
    assert (dest / "raii" / "SKILL.md").exists()
    assert "raii: installed" in capsys.readouterr().out


def test_cli_fails_when_no_built_skills(tmp_path, capsys):
    src = tmp_path / "repo"
    (src / "skills").mkdir(parents=True)

    assert main(["--repo-root", str(src), "--dest", str(tmp_path / "user-skills")]) == 1
    assert "no built skills found" in capsys.readouterr().out
