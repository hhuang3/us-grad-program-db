"""Incremental backup of data/snapshots (07 §10.2)."""


class BackupError(RuntimeError):
    """The destination holds a file that must not be overwritten."""


def backup(src, dest):
    raise NotImplementedError
