# Skill eval harness

The language for measuring whether an agent skill changes agent behaviour. The harness runs eval cases against skills and reports results over time.

## Language

**Skill**:
A folder with a `SKILL.md` that an agent can load, plus optional eval cases.
_Avoid_: Plugin, tool

**Case**:
One eval prompt for a skill, with checks that decide whether the run passed.
_Avoid_: Test, scenario

**Arm**:
The condition a run is executed under: "with" (skill available) or "without" (skill hidden).
_Avoid_: Variant, mode

**Run**:
One execution of one case, in a fresh session, on one model, under one arm.
_Avoid_: Trial, attempt

**Run group**:
The runs that share a skill, case, model, arm, and skill hash. N is the number of runs per group, so changing N adds runs to the group rather than starting a new one. Results are reported per group as k/N.
_Avoid_: Batch, set

**Skill hash**:
A content hash of a skill's `SKILL.md` and fixtures. Editing a skill starts a new run group.

**Pass**:
A run passes only if the skill loaded and all checks passed.
_Avoid_: Success
