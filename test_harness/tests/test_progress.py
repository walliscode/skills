import io

from test_harness import cli, progress


def test_render_shows_done_total_passed_skill_and_model_with_a_bar():
    text = progress.render(done=3, total=10, passed=2, skill="s/canary", model="m", width=10)

    assert "[###-------]" in text
    assert "3/10" in text
    assert "2 passed" in text
    assert "s/canary" in text
    assert "m" in text.split()


def test_non_terminal_prints_one_line_per_completed_run_and_no_bar():
    out = io.StringIO()
    bar = progress.Progress(total=2, stream=out, tty=False)

    bar.completed("PASS s c (m, with)", skill="s", model="m", passed=True)
    bar.completed("FAIL s c (m, without)", skill="s", model="m", passed=False)
    bar.close()

    assert out.getvalue() == "PASS s c (m, with)\nFAIL s c (m, without)\n"


def test_terminal_redraws_the_bar_and_keeps_completed_run_lines():
    out = io.StringIO()
    bar = progress.Progress(total=1, stream=out, tty=True)

    bar.completed("PASS s c (m, with)", skill="s", model="m", passed=True)
    bar.close()

    text = out.getvalue()
    assert "PASS s c (m, with)\n" in text
    assert "1/1" in text
    assert "1 passed" in text
    assert text.endswith("\n")


def test_progress_demo_runs_without_a_model(capsys):
    code = cli.main(["progress-demo", "--runs", "4", "--delay", "0"])

    assert code == 0
    assert len(capsys.readouterr().out.splitlines()) == 4


def test_start_shows_the_run_in_progress_on_the_bar():
    out = io.StringIO()
    bar = progress.Progress(total=2, stream=out, tty=True)

    bar.start(skill="s/other", model="m2")

    assert out.getvalue().endswith("s/other m2")
