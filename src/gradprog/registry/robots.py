"""robots.txt checks and crawl permission (06 §4)."""


def robots_verdicts(status_code, text, urls):
    raise NotImplementedError


def crawl_allowed_for(pages, domains):
    raise NotImplementedError


def check_robots(registry, contact_email=None, client=None, min_interval=3.0, clock=None, sleep=None,
                 now=None):
    raise NotImplementedError
