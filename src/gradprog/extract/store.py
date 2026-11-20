"""Local extraction files, which hold page text (08 §4), and the summary statistics kept in git."""

import json
from pathlib import Path

from gradprog.snapshot.store import _append

RUN_COLUMNS = ["run_id", "started_at", "finished_at", "model_name", "prompt_version", "schema_version",
               "extract_rules_version", "calls", "ok", "invalid_output", "api_error", "refusal", "max_tokens",
               "unavailable", "needs_review", "stopped_by_budget", "observations", "found", "in_review",
               "input_tokens", "cache_write_tokens", "cache_read_tokens", "output_tokens", "usd"]


class ExtractionStore:
    def __init__(self, root, stats_root):
        self.root, self.stats_root = Path(root), Path(stats_root)
        self.records_path = self.root / "page_records.jsonl"
        self.observations_path = self.root / "observations.jsonl"
        self.view_path = self.root / "derived" / "current.csv"
        self.runs_path = self.stats_root / "runs.csv"

    def call_path(self, call_id):
        return self.root / "calls" / f"{call_id}.json"

    def write_call(self, call_id, payload):
        path = self.call_path(call_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "x", encoding="utf-8") as f:      # stored outputs are never rewritten
            json.dump(payload, f, ensure_ascii=False, indent=1)

    def read_call(self, call_id):
        return json.loads(self.call_path(call_id).read_text(encoding="utf-8"))

    def _append_lines(self, path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:      # append only: existing lines are never rewritten
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _read_lines(path):
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def append_record(self, record):
        self._append_lines(self.records_path, [record])

    def read_records(self):
        return self._read_lines(self.records_path)

    def append_observations(self, rows):
        self._append_lines(self.observations_path, rows)

    def read_observations(self):
        return self._read_lines(self.observations_path)

    def spent_usd(self):
        return sum(r.get("usd", 0) for r in self.read_records())

    def append_run(self, row):
        _append(self.runs_path, RUN_COLUMNS, row)
