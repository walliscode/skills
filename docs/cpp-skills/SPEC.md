# C++ skill suite: spec and roadmap

## Destination

A small set of tested C++ units that the agent can use. Area skills are created only when they have a unit (see `docs/adr/0002-areas-created-with-first-unit.md`).

## Roadmap

1. **First pass (units):** file creation and templates, formatting (including `.clang-format`), Doxygen per function.
2. **Build and install:** the build script that combines units into area skills (`scripts/build_skill.py`), and the install script (`scripts/install_skills.py`). Both exist; the build script's check and build modes are now separate functions.
3. **Later:** larger topics, each started with its own grill-with-docs session.

## Problem Statement

C++ developers using an AI agent get inconsistent results. The agent places files in the wrong module, formats code inconsistently, leaves functions undocumented, and reinvents conventions every session. There is no small, tested body of C++ guidance for the agent to draw on.

## Solution

Build the C++ skill suite from small, individually tested units. The first pass covers three narrow units. Larger topics are deferred until they are grilled in their own session. Each area skill is created only once it has a unit, so the taxonomy grows from real content.

## First-pass units

1. **File creation and templates:** create new header and source files from templates that match project conventions, including header conventions and test scaffolding.
2. **Formatting:** apply the project formatter at the end of a change, and include the `.clang-format` config.
3. **Doxygen per function:** write a Doxygen comment for each function as it is finished.

## User Stories

1. As a C++ developer, I want the agent to create new header and source files from templates, so that new files match project conventions.
2. As a C++ developer, I want the agent to scaffold test files for new code, so that new code is tested from the start.
3. As a C++ developer, I want the agent to apply formatting at the end of a change, so that style is consistent.
4. As a C++ developer, I want a `.clang-format` config I can reuse, so that formatting is the same across projects.
5. As a C++ developer, I want a Doxygen comment written for each function as it is finished, so that documentation stays current.
6. As a skill maintainer, I want each unit built and tested on its own, so that a failing unit is easy to locate.
7. As a skill maintainer, I want each unit to start with a failing eval of the wanted behaviour, run without guidance, so that content is added only where the agent falls short.
8. As a skill maintainer, I want unit content combined into its area skill by a build step, so that each topic has one source of truth.
9. As a skill maintainer, I want the build to copy each unit's source path into the combined file, so that any line can be traced to its origin.
10. As a skill maintainer, I want the build to fail when committed combined files are stale, so that the repo never ships out-of-date skills.
11. As a skill maintainer, I want unit evals to run before the build and combined evals after it, stopping at the first failure.
12. As a skill maintainer, I want a script that installs built skills into my user-level skills folder, and that refuses to overwrite a skill it did not install.
13. As a skill maintainer, I want to write content for C++23 first, citing cppreference or the C++ Core Guidelines.

## Implementation Decisions

- **Units:** each topic is a unit with its own evals, in a folder under its area's `units/` directory. Area skills are created when they first have a unit.
- **Combined skills:** `scripts/build_skill.py` copies unit content into the area skill, with a `<!-- source: ... -->` marker before each block. Built output is committed (see `docs/adr/0001-combined-skills-built-from-units.md`).
- **Pipeline order:** unit evals, then build, then a freshness check against committed output, then combined evals. Stop at the first failure. `make check-skills` runs the freshness check.
- **Install script:** copies built skills into the user-level skills folder, run by hand with `make install-skills`. Refuses to overwrite a skill folder it did not install. Users update by pulling and re-running it.
- **Evals:** the existing harness (`test_harness/`) runs every unit and combined skill.
- **Content rules:** add information only when a failing eval shows the agent needs it. Cite cppreference or the C++ Core Guidelines. Write C++23 first.
- **Compiler support:** C++23 feature recommendations follow `research/cpp23-feature-support.md`. Features that are partial, missing on libc++, or version-gated carry a caution or version gate.
- **Glossary:** terms are defined in `cpp-skills/CONTEXT.md`.

## Testing Decisions

- **What makes a good test:** test external behaviour only: what the agent does with a prompt, and whether the output and files it writes are right. Do not test the wording of a skill.
- **Seams:** the eval harness runs each unit and combined skill. The build script's pipeline runs the steps in order.
- **Modules tested:** the build script (pipeline order, stop on first failure, freshness check, source markers) and the install script (copy, refuse to overwrite). Run with `make test-scripts`.
- **Prior art:** the harness fixture `harness-fixtures/canary-word` and its eval cases.

## Deferred

Each of these gets its own grill-with-docs session when it is time:

- Language core: RAII and ownership first, then move semantics, templates and concepts, lambdas and constexpr, modules, error handling.
- Build and tooling beyond formatting: package managers, CMake, sanitizers, static analysis, warnings, codebase structure.
- Testing, debugging and performance, concurrency, standard library, review and style.
- The project quiz, which recommends skills that do not exist yet.

## Open items

- The C++23 research has open cross-checks: the MSVC version-to-Visual-Studio mapping, and the Clang 23 and libc++ 22/23 entries against the libc++ status page. See the research file.

## Out of Scope

- Compile-and-run checks, which belong to a separate in-repo skill.
- File-level headers (Doxygen file comments and licence headers).
- Standards older than C++23, until they are needed.
- A release or versioned-package install.
