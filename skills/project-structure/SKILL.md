---
name: project-structure
description: Use when creating a new C++ header and source file, or deciding where it goes in a project.
---

<!-- source: cpp-skills/project-structure/units/file-creation/UNIT.md -->
# Creating a new C++ header and source pair

Create the pair with `cpp-skills/project-structure/units/file-creation/new_cpp_file.sh`, run from the repo root. Do not write the files by hand.

- PascalCase name (`ParserState`): class or struct.
- snake_case name (`parse_headers`): free functions.
- A free function with a PascalCase name: do not create it. Ask the user for a snake_case name.

Before running, confirm the directory and the namespace (the directory with `/` replaced by `::`) with the user.
