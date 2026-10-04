"""Classification, previous-version selection and diffs (07 §7)."""


def load_thresholds(path):
    raise NotImplementedError


def similarity(prev_text, new_text):
    raise NotImplementedError


def classify_content(prev_text, new_text, thresholds):
    raise NotImplementedError


def make_diff(prev_text, new_text, prev_id, new_id):
    raise NotImplementedError


def select_prev(index, page_id, retrieved_at, snapshot_id, version):
    raise NotImplementedError
