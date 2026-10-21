"""Copy built skills into the user-level skills folder.

Each ``skills/<name>/SKILL.md`` is installed to ``<dest>/<name>/SKILL.md``. A
marker file records that this script installed the folder, so later runs can
update it. A folder without the marker is left untouched and reported.
"""

import argparse
import shutil
import sys
from pathlib import Path

MARKER = ".installed-by-install-skills"
DEFAULT_DEST = Path.home() / ".agents" / "skills"


def install(repo_root: Path, dest: Path) -> dict[str, str]:
    report = {}
    for built in sorted((repo_root / "skills").glob("*/SKILL.md")):
        name = built.parent.name
        target = dest / name
        if target.exists() and not (target / MARKER).exists():
            report[name] = "skipped: not installed by this script"
            continue
        status = "updated" if target.exists() else "installed"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built, target / "SKILL.md")
        (target / MARKER).write_text("installed by scripts/install_skills.py\n")
        report[name] = status
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install built skills into the user-level skills folder.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    args = parser.parse_args(argv)

    report = install(args.repo_root.resolve(), args.dest)
    for name, status in report.items():
        print(f"{name}: {status}")
    if not report:
        print("no built skills found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
