"""Registry tables: init, load/save, add-page, derive (06 §3, §4.2, §6)."""


class RegistryError(ValueError):
    """Registry operation violates a documented rule."""


class Registry:
    def __init__(self, programs, pages, program_pages, domains):
        raise NotImplementedError


def init_registry(registry_dir):
    raise NotImplementedError


def load_registry(registry_dir):
    raise NotImplementedError


def save_registry(registry, registry_dir):
    raise NotImplementedError


def add_page(registry, url, page_type, owner_level, content_format, program_ids, added_at,
             url_status="proposed"):
    raise NotImplementedError


def derive(registry):
    raise NotImplementedError
