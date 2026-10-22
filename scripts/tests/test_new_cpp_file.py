import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "cpp-skills" / "project-structure" / "units" / "file-creation" / "new_cpp_file.sh"


def run(cwd, *args):
    return subprocess.run(["bash", str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True)


def test_pascal_case_name_writes_hpp_and_cpp_with_derived_namespace(tmp_path):
    result = run(tmp_path, "--dir", "mylib/net/http", "--name", "ParserState")

    assert result.returncode == 0
    hpp = (tmp_path / "mylib/net/http/ParserState.hpp").read_text()
    cpp = (tmp_path / "mylib/net/http/ParserState.cpp").read_text()
    assert "#pragma once" in hpp
    assert "namespace mylib::net::http {" in hpp
    assert "}  // namespace mylib::net::http" in hpp
    assert "namespace mylib::net::http {" in cpp
    assert "#pragma once" not in cpp


def test_snake_case_name_writes_matching_pair(tmp_path):
    result = run(tmp_path, "--dir", "mylib", "--name", "parse_headers")

    assert result.returncode == 0
    assert (tmp_path / "mylib/parse_headers.hpp").exists()
    assert (tmp_path / "mylib/parse_headers.cpp").exists()


def test_both_files_have_banner_and_empty_headers_section(tmp_path):
    run(tmp_path, "--dir", "mylib", "--name", "parse_headers")

    for ext in ("hpp", "cpp"):
        text = (tmp_path / f"mylib/parse_headers.{ext}").read_text()
        assert text.startswith("/**\n * @file parse_headers." + ext + "\n * @brief\n */\n")
        assert "// headers\n" in text


def assert_rejected_without_files(tmp_path, dir_arg, name_arg):
    result = run(tmp_path, "--dir", dir_arg, "--name", name_arg)

    assert result.returncode != 0
    assert not any(tmp_path.iterdir())


def test_kebab_case_name_is_rejected(tmp_path):
    assert_rejected_without_files(tmp_path, "mylib", "parse-headers")


def test_directory_component_that_is_not_snake_case_is_rejected(tmp_path):
    assert_rejected_without_files(tmp_path, "MyLib", "ParserState")


def test_absolute_path_is_rejected(tmp_path):
    assert_rejected_without_files(tmp_path, str(tmp_path / "mylib"), "ParserState")


def test_path_containing_dotdot_is_rejected(tmp_path):
    assert_rejected_without_files(tmp_path, "mylib/../other", "ParserState")


def test_existing_hpp_blocks_both_files_and_leaves_it_unchanged(tmp_path):
    folder = tmp_path / "mylib"
    folder.mkdir()
    (folder / "ParserState.hpp").write_text("original hpp\n")

    result = run(tmp_path, "--dir", "mylib", "--name", "ParserState")

    assert result.returncode != 0
    assert (folder / "ParserState.hpp").read_text() == "original hpp\n"
    assert not (folder / "ParserState.cpp").exists()


def test_existing_cpp_blocks_both_files_and_leaves_it_unchanged(tmp_path):
    folder = tmp_path / "mylib"
    folder.mkdir()
    (folder / "ParserState.cpp").write_text("original cpp\n")

    result = run(tmp_path, "--dir", "mylib", "--name", "ParserState")

    assert result.returncode != 0
    assert (folder / "ParserState.cpp").read_text() == "original cpp\n"
    assert not (folder / "ParserState.hpp").exists()


def test_missing_arguments_exit_with_usage_error(tmp_path):
    result = run(tmp_path, "--name", "ParserState")

    assert result.returncode == 2
    assert not any(tmp_path.iterdir())
