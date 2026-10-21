"""Build a combined skill from a skill spec.

A skill spec is ``skills/<name>/skill.yaml`` with ``name``, ``description`` and
an ordered ``units`` list of markdown files (paths relative to the repo root).
Each unit is copied in order, preceded by a ``<!-- source: <path> -->`` marker.
The result is written to ``skills/<name>/SKILL.md``.
"""

import argparse
import sys
from pathlib import Path

import yaml


class BuildError(Exception):
    pass


def load_spec(spec: Path) -> dict:
    if not spec.is_file():
        raise BuildError(f"skill spec not found: {spec}")
    data = yaml.safe_load(spec.read_text()) or {}
    if not data.get("units"):
        raise BuildError(f"{spec}: no units listed")
    return data


def build_skill(spec: Path, repo_root: Path) -> str:
    data = load_spec(spec)
    blocks = []
    for path in data["units"]:
        source = repo_root / path
        if not source.is_file():
            raise BuildError(f"{spec.parent.name}: unit not found: {path}")
        content = source.read_text().rstrip("\n") + "\n"
        blocks.append(f"<!-- source: {path} -->\n{content}")
    header = f"---\nname: {data['name']}\ndescription: {data['description']}\n---\n\n"
    return header + "\n".join(blocks)


def output_path(spec: Path) -> Path:
    return spec.parent / "SKILL.md"


def write_skill(spec: Path, repo_root: Path) -> Path:
    out = output_path(spec)
    out.write_text(build_skill(spec, repo_root))
    return out


def is_fresh(spec: Path, repo_root: Path) -> bool:
    built = build_skill(spec, repo_root)
    out = output_path(spec)
    return out.is_file() and out.read_text() == built


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build combined skills from skill specs.")
    parser.add_argument("specs", nargs="+", type=Path, help="skill spec files")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if committed output differs from the build",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    status = 0
    for name in args.specs:
        spec = (repo_root / name).resolve()
        try:
            if args.check:
                if not is_fresh(spec, repo_root):
                    print(f"stale: {output_path(spec).relative_to(repo_root)}", file=sys.stderr)
                    status = 1
            else:
                out = write_skill(spec, repo_root)
                print(f"built: {out.relative_to(repo_root)}")
        except BuildError as err:
            print(f"error: {err}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
