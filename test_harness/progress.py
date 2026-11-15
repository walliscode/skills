"""@file progress.py
@brief Progress output for a batch run: one live bar on a terminal, one line per completed run otherwise.
"""

# Standard library: writing to the terminal and flushing.
import sys

# Width, in characters, of the bar drawn between the brackets.
BAR_WIDTH = 30


def render(done, total, passed, skill, model, width=BAR_WIDTH):
    """@brief Build the progress bar text for the current state of a batch.

    @param done Runs completed so far.
    @param total Runs in the batch.
    @param passed Runs that passed so far.
    @param skill The skill of the most recent run.
    @param model The model of the most recent run.
    @param width Characters in the bar.
    @return One line, e.g. `[###-------] 3/10 runs, 2 passed  skill model`.
    """
    filled = int(width * done / total) if total else width
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {done}/{total} runs, {passed} passed  {skill} {model}"


class Progress:
    """@brief Track a batch's runs and write their progress to a stream."""

    def __init__(self, total, stream=None, tty=None):
        """@brief Start a progress display for `total` runs.

        @param total Runs in the batch.
        @param stream Where to write. Defaults to stdout.
        @param tty Whether to draw a live bar. Defaults to whether the stream is a terminal.
        """
        self.total = total
        self.stream = sys.stdout if stream is None else stream
        self.tty = self.stream.isatty() if tty is None else tty
        self.done = 0
        self.passed = 0
        self.skill = ""
        self.model = ""
        if self.tty:
            self._draw()

    def completed(self, line, skill, model, passed):
        """@brief Record one finished run and write its line.

        On a terminal the line stays above the bar, which is redrawn below it.

        @param line The text to print for this run.
        @param skill The run's skill.
        @param model The run's model.
        @param passed Whether the run passed.
        """
        self.done += 1
        self.passed += int(passed)
        self.skill = skill
        self.model = model
        if self.tty:
            self.stream.write(f"\r\x1b[2K{line}\n")
            self._draw()
        else:
            self.stream.write(f"{line}\n")
        self.stream.flush()

    def close(self):
        """@brief Leave the bar on its own line, so later output starts clean."""
        if self.tty:
            self.stream.write("\n")
            self.stream.flush()

    def _draw(self):
        """@brief Redraw the bar on the current line."""
        text = render(self.done, self.total, self.passed, self.skill, self.model)
        self.stream.write(f"\r\x1b[2K{text}")
        self.stream.flush()
