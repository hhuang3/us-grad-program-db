"""Snapshot storage layout, index.csv and runs.csv (07 §4)."""


class SnapshotError(ValueError):
    """A snapshot operation violates a documented rule."""


def make_snapshot_id(retrieved_at, page_id):
    raise NotImplementedError


def make_run_id(started_at, method):
    raise NotImplementedError


class SnapshotStore:
    def __init__(self, root):
        raise NotImplementedError

    def raw_path(self, page_id, snapshot_id, ext):
        raise NotImplementedError

    def norm_path(self, page_id, snapshot_id, version):
        raise NotImplementedError

    def diff_path(self, page_id, snapshot_id, version):
        raise NotImplementedError

    def read_index(self):
        raise NotImplementedError

    def append_index(self, row):
        raise NotImplementedError

    def read_runs(self):
        raise NotImplementedError

    def append_run(self, row):
        raise NotImplementedError
