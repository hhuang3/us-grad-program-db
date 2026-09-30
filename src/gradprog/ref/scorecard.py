"""College Scorecard Field of Study filtering (docs/spec/01_reference_data.md §5, 04 §6)."""


class ScorecardValueError(ValueError):
    """A Scorecard metric value is neither numeric nor a documented missing code."""


def parse_metric(raw):
    raise NotImplementedError


def build_scorecard_fos_target(raw, targets, cip2020):
    raise NotImplementedError
