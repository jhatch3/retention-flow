"""Tests for the dbt-output parsing constants in backend.api.rebuild.

`rebuild_events` streams dbt's stdout; `_KEEP` filters it to status lines and
`_NODE` extracts the "<n> of <total>" progress counter used for the progress
bar. These tests pin that parsing against representative dbt output.
"""

from backend.api.rebuild import _KEEP, _NODE


def test_node_regex_extracts_the_progress_counter():
    match = _NODE.search("01:23:45  3 of 26 OK created sql view model staging.x")
    assert match is not None
    assert match.group(1) == "3"
    assert match.group(2) == "26"


def test_node_regex_does_not_match_lines_without_a_counter():
    assert _NODE.search("Running with dbt=1.8.0") is None


def test_keep_filter_selects_dbt_status_lines():
    status_lines = [
        "01:23:45  3 of 26 OK created sql view model staging.x",
        "01:23:46  4 of 26 PASS not_null_orders ...",
        "01:23:47  5 of 26 ERROR creating sql table model marts.y",
        "01:23:48  Completed successfully",
    ]
    for line in status_lines:
        assert any(token in line for token in _KEEP)


def test_keep_filter_drops_noise_lines():
    noise_lines = [
        "01:23:45  Concurrency: 4 threads (target='dev')",
        "01:23:45  Found 6 models, 12 tests, 9 sources",
    ]
    for line in noise_lines:
        assert not any(token in line for token in _KEEP)
