import json
import os

OUTCOMES_PATH = os.path.join(os.path.dirname(__file__), "..", "outcomes.jsonl")


class Monitor:
    """Bare-bones outcome logger. No aggregation, no dashboard -- extend this."""

    def __init__(self, path=OUTCOMES_PATH):
        self.path = path

    def record(self, outcome: dict):
        if "winner" not in outcome:
            return
        with open(self.path, "a") as f:
            f.write(json.dumps(outcome) + "\n")

    def count(self) -> int:
        """Return number of logged outcomes. Not wired into simulate yet."""
        try:
            with open(self.path) as f:
                return sum(1 for _ in f)
        except FileNotFoundError:
            return 0
