# Agent Skills spec: SKILL.md format and frontmatter rules

Primary source: Agent Skills specification, https://agentskills.io/specification
Validator: skills-ref, https://github.com/agentskills/agentskills/tree/main/skills-ref

## Directory layout

A skill is a directory containing at minimum `SKILL.md`:

```
skill-name/
├── SKILL.md      # required: frontmatter + instructions
├── scripts/      # optional: executable code
├── references/   # optional: docs loaded on demand
├── assets/       # optional: templates, images, data files
└── ...           # any other files or directories
```

The `scripts/`, `references/`, and `assets/` names are recommendations, not requirements.

## SKILL.md frontmatter

YAML frontmatter followed by Markdown body.

| Field | Required | Constraints |
| - | - | - |
| `name` | Yes | 1-64 chars. Lowercase `a-z`, `0-9`, and `-` only. No leading/trailing hyphen, no `--`. Must match the parent directory name. |
| `description` | Yes | 1-1024 chars, non-empty. Say what the skill does and when to use it. |
| `license` | No | License name or reference to a bundled license file. |
| `compatibility` | No | 1-500 chars. Environment requirements (product, system packages, network). Most skills omit it. |
| `metadata` | No | String-to-string map for extra properties. Use reasonably unique keys. |
| `allowed-tools` | No | Space-separated pre-approved tools, e.g. `Bash(git:*) Read`. Experimental. |

Body: no format restrictions. Recommended sections are step-by-step instructions, input/output examples, and edge cases.

## Progressive disclosure and resources

1. Metadata (`name`, `description`) loaded at startup for all skills (~100 tokens).
2. Full `SKILL.md` body loaded on activation (recommended < 5000 tokens).
3. Files in `scripts/`, `references/`, `assets/` loaded only when needed.

Keep `SKILL.md` under 500 lines. Move detail into reference files.
File references use paths relative to the skill root and stay one level deep from `SKILL.md`.

## Implications for this repo

- Each skill module needs its own directory whose name equals the frontmatter `name`.
- `name` must be lowercase-hyphenated; `description` must be present and at most 1024 chars.
- Put bulky material in `references/` and link it from `SKILL.md` one level deep.
- Run `skills-ref validate ./<skill>` to check conformance.
