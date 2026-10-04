"""Manual captures: due list and registration (07 §5.2)."""


def manual_due(registry, store, today, url_check=None):
    raise NotImplementedError


def render_manual_due(due):
    raise NotImplementedError


def register_manual(registry, store, page_id, file, retrieved_at=None, now=None, thresholds=None, rules=None,
                    url_check=None):
    raise NotImplementedError


def register_from_dir(registry, store, directory, retrieved_at=None, now=None, thresholds=None, rules=None,
                      url_check=None):
    raise NotImplementedError
