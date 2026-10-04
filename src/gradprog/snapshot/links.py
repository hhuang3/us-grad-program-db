"""Link discovery on program home pages (07 §8)."""


def registrable_domain(host):
    raise NotImplementedError


def load_keywords(path):
    raise NotImplementedError


def discover_links(raw_html, base_url, registered_urls, keywords):
    raise NotImplementedError
