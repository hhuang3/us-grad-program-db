"""Text normalization of HTML, MHTML and PDF snapshots (07 §6)."""


def load_rules(path):
    raise NotImplementedError


def mhtml_location(raw):
    raise NotImplementedError


def normalize(raw, content_type, domain=None, rules=None, charset=None):
    raise NotImplementedError
