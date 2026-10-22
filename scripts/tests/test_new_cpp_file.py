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


def test_missing_arguments_exit_with_usage_error(tmp_path):
    result = run(tmp_path, "--name", "ParserState")

    assert result.returncode == 2
    assert not any(tmp_path.iterdir())
