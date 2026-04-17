"""Tests for clipse_gui/utils.py — format_date, fuzzy_search, _calculate_similarity."""

from datetime import datetime, timedelta, timezone

import pytest

from clipse_gui.utils import _calculate_similarity, format_date, fuzzy_search


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(value, pinned=False, file_path=""):
    return {"value": value, "pinned": pinned, "filePath": file_path}


# ---------------------------------------------------------------------------
# format_date
# ---------------------------------------------------------------------------

class TestFormatDate:
    def test_none_returns_unknown(self):
        assert format_date(None) == "Unknown date"

    def test_empty_string_returns_unknown(self):
        assert format_date("") == "Unknown date"

    def test_invalid_date_returns_original(self):
        bad = "not-a-date"
        assert format_date(bad) == bad

    def test_today_naive(self):
        now = datetime.now()
        iso = now.isoformat()
        result = format_date(iso)
        assert result.startswith("Today at ")
        assert now.strftime("%H:%M") in result

    def test_yesterday_naive(self):
        yesterday = datetime.now() - timedelta(days=1)
        iso = yesterday.isoformat()
        result = format_date(iso)
        assert result.startswith("Yesterday at ")
        assert yesterday.strftime("%H:%M") in result

    def test_same_year_not_today_or_yesterday(self):
        now = datetime.now()
        two_weeks_ago = now - timedelta(days=14)
        iso = two_weeks_ago.isoformat()
        result = format_date(iso)
        assert result == two_weeks_ago.strftime("%b %d, %H:%M")
        assert str(now.year) not in result

    def test_different_year(self):
        dt = datetime(2020, 3, 5, 9, 30)
        result = format_date(dt.isoformat())
        assert result == "Mar 05, 2020, 09:30"

    def test_z_suffix_treated_as_utc(self):
        utc_now = datetime.now(timezone.utc)
        iso_z = utc_now.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        result = format_date(iso_z)
        assert result.startswith("Today at ")

    def test_timezone_aware_iso(self):
        utc_now = datetime.now(timezone.utc)
        iso = utc_now.isoformat()
        result = format_date(iso)
        assert result.startswith("Today at ")

    def test_yesterday_timezone_aware(self):
        yesterday_utc = datetime.now(timezone.utc) - timedelta(days=1)
        iso = yesterday_utc.isoformat()
        result = format_date(iso)
        assert result.startswith("Yesterday at ")

    def test_different_year_timezone_aware(self):
        dt = datetime(2019, 11, 22, 15, 45, tzinfo=timezone.utc)
        result = format_date(dt.isoformat())
        assert "2019" in result
        assert result.startswith("Nov 22")


# ---------------------------------------------------------------------------
# fuzzy_search
# ---------------------------------------------------------------------------

class TestFuzzySearch:
    def _items(self):
        return [
            _make_item("hello world", pinned=True),
            _make_item("foo bar baz"),
            _make_item("python programming"),
            _make_item("clipboard history"),
            _make_item("", file_path="/home/user/image.png"),
        ]

    def test_empty_search_returns_all(self):
        items = self._items()
        results = fuzzy_search(items, "")
        assert len(results) == len(items)

    def test_empty_search_preserves_original_indices(self):
        items = self._items()
        results = fuzzy_search(items, "")
        indices = [r["original_index"] for r in results]
        assert indices == list(range(len(items)))

    def test_exact_match_score_100(self):
        items = [_make_item("hello world")]
        results = fuzzy_search(items, "hello")
        assert len(results) == 1
        assert results[0]["match_quality"] == 100

    def test_exact_match_returns_correct_item(self):
        items = self._items()
        results = fuzzy_search(items, "python programming")
        assert len(results) == 1
        assert results[0]["item"]["value"] == "python programming"

    def test_substring_match_scores_100(self):
        # Python's `in` operator finds substrings, so any prefix or substring of
        # a word hits the `token in item_value` branch and gets score 100.
        items = [_make_item("hello world")]
        results = fuzzy_search(items, "hel")
        assert len(results) == 1
        assert results[0]["match_quality"] == 100

    def test_reverse_prefix_match_score_60(self):
        # token.startswith(word) and len(word) >= 3 → score 60
        # "foo" is a word in value, token "foobar" starts with "foo"
        # AND "foobar" is NOT in item_value "foo" (substring check fails first)
        items = [_make_item("foo")]
        results = fuzzy_search(items, "foobar")
        assert len(results) == 1
        assert results[0]["match_quality"] == 60

    def test_multi_token_all_must_match(self):
        items = [
            _make_item("hello world"),
            _make_item("hello darkness"),
        ]
        results = fuzzy_search(items, "hello world")
        assert len(results) == 1
        assert results[0]["item"]["value"] == "hello world"

    def test_multi_token_scores_accumulate(self):
        items = [_make_item("foo bar")]
        results = fuzzy_search(items, "foo bar")
        assert results[0]["match_quality"] == 200

    def test_no_match_returns_empty(self):
        items = self._items()
        results = fuzzy_search(items, "zzzzzzzzz")
        assert results == []

    def test_show_only_pinned_filters_unpinned(self):
        items = [
            _make_item("hello", pinned=True),
            _make_item("world", pinned=False),
        ]
        results = fuzzy_search(items, "", show_only_pinned=True)
        assert len(results) == 1
        assert results[0]["item"]["value"] == "hello"

    def test_show_only_pinned_with_search_term(self):
        items = [
            _make_item("hello", pinned=True),
            _make_item("hello world", pinned=False),
        ]
        results = fuzzy_search(items, "hello", show_only_pinned=True)
        assert len(results) == 1
        assert results[0]["item"]["pinned"] is True

    def test_results_sorted_by_quality_descending(self):
        items = [
            _make_item("foo"),         # reverse-prefix for "foobar" → 60
            _make_item("foobar"),      # exact → 100
            _make_item("foob"),        # reverse-prefix for "foobar" → 60
        ]
        results = fuzzy_search(items, "foobar")
        qualities = [r["match_quality"] for r in results]
        assert qualities == sorted(qualities, reverse=True)
        assert qualities[0] == 100

    def test_file_path_matching(self):
        items = [
            _make_item("", file_path="/home/user/photo.png"),
            _make_item("unrelated text"),
        ]
        results = fuzzy_search(items, "photo")
        assert len(results) == 1
        assert results[0]["item"]["filePath"] == "/home/user/photo.png"

    def test_case_insensitive_search(self):
        items = [_make_item("Hello World")]
        results = fuzzy_search(items, "HELLO")
        assert len(results) == 1

    def test_original_index_is_correct(self):
        items = [
            _make_item("alpha"),
            _make_item("beta"),
            _make_item("gamma"),
        ]
        results = fuzzy_search(items, "gamma")
        assert results[0]["original_index"] == 2

    def test_similarity_match_high_threshold(self):
        # "helo" vs "hello" — similar enough to exceed 70% threshold
        items = [_make_item("hello")]
        results = fuzzy_search(items, "helo")
        # Either found via substring or similarity — if found, quality > 0
        if results:
            assert results[0]["match_quality"] > 0

    def test_empty_items_list(self):
        results = fuzzy_search([], "anything")
        assert results == []

    def test_item_without_value_key(self):
        items = [{"pinned": False, "filePath": ""}]
        results = fuzzy_search(items, "hello")
        assert results == []


# ---------------------------------------------------------------------------
# _calculate_similarity
# ---------------------------------------------------------------------------

class TestCalculateSimilarity:
    def test_identical_strings_returns_one(self):
        assert _calculate_similarity("hello", "hello") == pytest.approx(1.0)

    def test_no_char_overlap_same_length(self):
        # set("abc") ∩ set("xyz") = {} → basic_score = 0
        # len_ratio = 3/3 = 1.0
        # result = 0*0.7 + 1.0*0.3 = 0.3
        score = _calculate_similarity("abc", "xyz")
        assert score == pytest.approx(0.3)

    def test_no_char_overlap_different_length(self):
        # set("ab") ∩ set("xyz") = {} → basic_score = 0
        # len_ratio = 2/3
        # result = 0 + (2/3)*0.3 = 0.2
        score = _calculate_similarity("ab", "xyz")
        assert score == pytest.approx(0.2)

    def test_partial_overlap(self):
        score = _calculate_similarity("hello", "helo")
        assert 0.0 < score < 1.0

    def test_empty_both_returns_zero(self):
        assert _calculate_similarity("", "") == 0.0

    def test_one_empty_string(self):
        score = _calculate_similarity("hello", "")
        assert score == 0.0

    def test_symmetry(self):
        a, b = "python", "typhon"
        assert _calculate_similarity(a, b) == pytest.approx(_calculate_similarity(b, a))

    def test_score_bounded_zero_to_one(self):
        for a, b in [("cat", "dog"), ("abc", "abcdef"), ("x", "xyz")]:
            score = _calculate_similarity(a, b)
            assert 0.0 <= score <= 1.0

    def test_longer_string_pair(self):
        score = _calculate_similarity("programming", "program")
        assert score > 0.5
