"""@file run.py
@brief Run the planned eval cases under both arms, grade each run, and write its result.
"""

# Standard library: deleting workspaces, printing errors and paths.
import shutil
import sys

from test_harness import harness, progress

# The two arms every case runs under, in order: skill available, then skill denied.
ARMS = ("with", "without")


def run_plan(root, plan, model, config):
    """@brief Run every planned case under both arms, `runs` times each, and write one result per run.

    Stops at the first opencode error, keeping the results already written.

    @param root Repo root that holds the skill folders and the results folder.
    @param plan List of `(skill, case_dict)` pairs, in run order, from the CLI planner.
    @param model The `provider/model` string passed to opencode.
    @param config The loaded harness config.
    @return The process exit code: 0 if every "with" run passed, 1 if any failed, 2 for opencode or export errors.
    """
    # Sent verbatim. Both arms run for every case: "with" leaves the skill
    # available, "without" denies it. Only the "with" arm decides the exit code,
    # since "without" is the baseline and is expected to fail the checks.
    # Starts as passing and is turned off by any failing "with" run.
    all_passed = True
    # Starts as clear and is turned on by any run whose session export failed.
    export_failed = False
    bar = progress.Progress(len(plan) * len(ARMS) * config["runs"])
    for skill, case in plan:
        skill_hash = harness.skill_hash(root / skill)
        for arm in ARMS:
            # Repeat each arm N times, from the config's `runs` value.
            for _ in range(config["runs"]):
                # A new workspace for each run, so no run sees another's files.
                workspace = harness.make_workspace(root, skill, case["id"], arm=arm)
                try:
                    # Run the prompt in the workspace, then grade the result there.
                    events = harness.run_opencode(case["prompt"], model, cwd=workspace)
                    # Export the session for its cost and token counts. A failed export is recorded on the run, and the batch carries on.
                    export_error = None
                    try:
                        session = harness.export_session(harness.session_id(events), cwd=workspace)
                    except harness.ExportError as err:
                        # Usage data is optional, so this run is stored with null usage and the error text.
                        session = None
                        export_error = str(err)
                        # Remember the failure so the batch exits 2 once every run has finished.
                        export_failed = True
                        print(f"error: export failed for {skill} {case['id']} ({arm}): {err}", file=sys.stderr)
                    record = harness.build_record(
                        skill,
                        case["id"],
                        model,
                        case,
                        events,
                        arm=arm,
                        workspace=workspace,
                        judge=lambda criteria, output: harness.grade_rubric(criteria, output, model),
                        session=session,
                        skill_hash=skill_hash,
                        n=config["runs"],
                        export_error=export_error,
                    )
                except harness.OpencodeError as err:
                    # opencode itself failed, so this is an error (exit 2), not a graded FAIL.
                    bar.close()
                    print(f"error: {err}", file=sys.stderr)
                    return 2
                finally:
                    # Always delete the workspace, even on error. Grading has already read the files.
                    shutil.rmtree(workspace, ignore_errors=True)

                # Save the graded record to test_harness/results/.
                harness.write_result(root / "test_harness" / "results", record)

                passed = record["passed"]
                if arm == "with":
                    # Only "with" runs affect the exit code. A single failure makes it 1.
                    all_passed = all_passed and passed
                # One line per completed run, shown above the live bar on a terminal.
                bar.completed(
                    f"{'PASS' if passed else 'FAIL'} {skill} {case['id']} ({model}, {arm})",
                    skill=skill,
                    model=model,
                    passed=passed,
                )
    bar.close()
    # 2 if any session export failed, since that is an opencode error. Otherwise 0 if every "with" run passed, 1 if not.
    if export_failed:
        return 2
    return 0 if all_passed else 1
