# Creating a new C++ header and source pair

Create a new `.hpp` and `.cpp` pair by running the project command, not by writing the files by hand:

```bash
cpp-skills/project-structure/units/file-creation/new_cpp_file.sh --dir <dir> --name <name>
```

Run it from the repo root. The command writes both files with the project banner, `#pragma once` in the header, an empty headers section, and a namespace derived from the directory.

## Choosing the name

- **PascalCase** (`ParserState`) for a class or struct.
- **snake_case** (`parse_headers`) for free functions.

The command accepts either form. The casing tells the reader what the file holds, so pick it from the content.

## Before you run it

Suggest the directory and the namespace it will produce, and wait for the user to confirm both before running the command. The namespace is the directory with `/` replaced by `::`, so `mylib/net/http` gives `mylib::net::http`.

Directory components must be snake_case, and the path must be relative to the repo root with no `..`.

## If the command refuses

If the command exits non-zero, do not write the files by hand and do not remove the existing files. Report the message to the user and ask how to proceed.
