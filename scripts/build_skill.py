"""Build a combined skill from one unit directory.

A unit is a directory under ``units/`` holding a ``SKILL.md`` whose lines of
the form ``@include <path>`` are replaced by the file at ``<path>`` (relative to
the repo root), preceded by a ``<!-- source: <path> -->`` marker. The result is
written to ``skills/<unit name>/SKILL.md``.
"""

import argparse
import re
import sys
from pathlib import Path

INCLUDE = re.compile(r"^@include (\S+)\s*$")


class BuildError(Exception):
    pass


def build_unit(unit_dir: Path, repo_root: Path) -> str:
    lines = (unit_dir / "SKILL.md").read_text().splitlines(keepends=True)
    out = []
    for line in lines:
        match = INCLUDE.match(line)
        if not match:
            out.append(line)
            continue
        path = match.group(1)
        source = repo_root / path
        if not source.is_file():
            raise BuildError(f"{unit_dir.name}: include not found: {path}")
        content = source.read_text()
        if content and not content.endswith("\n"):
            content += "\n"
        out.append(f"<!-- source: {path} -->\n{content}")
    return "".join(out)


def output_path(unit_dir: Path, repo_root: Path) -> Path:
    return repo_root / "skills" / unit_dir.name / "SKILL.md"


def write_skill(unit_dir: Path, repo_root: Path) -> Path:
    out = output_path(unit_dir, repo_root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_unit(unit_dir, repo_root))
    return out


def is_fresh(unit_dir: Path, repo_root: Path) -> bool:
    out = output_path(unit_dir, repo_root)
    return out.is_file() and out.read_text() == build_unit(unit_dir, repo_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a combined skill from unit directories.")
    parser.add_argument("units", nargs="+", type=Path, help="unit directories")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if committed output differs from the build",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    status = 0
    for unit in args.units:
        unit_dir = (repo_root / unit).resolve()
        try:
            if args.check:
                if not is_fresh(unit_dir, repo_root):
                    print(f"stale: {output_path(unit_dir, repo_root).relative_to(repo_root)}", file=sys.stderr)
                    status = 1
            else:
                out = write_skill(unit_dir, repo_root)
                print(f"built: {out.relative_to(repo_root)}")
        except BuildError as err:
            print(f"error: {err}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
