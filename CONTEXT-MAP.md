# Context Map

## Contexts

- [Skill eval harness](./CONTEXT.md): measures whether an agent skill changes agent behaviour
- [C++ skill suite](./cpp-skills/CONTEXT.md): builds and ships the C++ skills that the harness evaluates

## Relationships

- **C++ skill suite → Skill eval harness**: each suite skill is tested by the harness, using its cases and arms
