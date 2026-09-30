"""Raw-file manifest and derived-table lineage (docs/spec/01_reference_data.md §6)."""


class ManifestError(ValueError):
    """A manifest row violates the manifest rules."""


def sha256_file(path):
    raise NotImplementedError


def raw_path_for(raw_root, source, url, retrieved_at):
    raise NotImplementedError


def append_manifest(manifest_path, row):
    raise NotImplementedError


def read_manifest(manifest_path):
    raise NotImplementedError


def record_derived(derived_path, table_path, input_sha256s, generated_at):
    raise NotImplementedError


def check_lineage(ref_dir, manifest_path, derived_path):
    raise NotImplementedError
