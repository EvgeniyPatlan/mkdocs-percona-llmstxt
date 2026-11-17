"""Tests for percona_llmstxt.nav."""

from __future__ import annotations

from typing import Any

import pytest

from percona_llmstxt.nav import nav_pages, sections_from_nav


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ("page.md", ["page.md"]),
        ("https://example.com/", []),
        ({"Title": "page.md"}, ["page.md"]),
        ({"Old releases": "https://example.com/"}, []),
        (["a.md", {"B": "b.md"}, {"Group": ["c.md", {"Sub": [{"D": "d.md"}]}]}], ["a.md", "b.md", "c.md", "d.md"]),
        (None, []),
        (42, []),
    ],
)
def test_nav_pages(item: Any, expected: list[str]) -> None:
    assert nav_pages(item) == expected


def test_top_level_groups_become_sections_and_loose_pages_come_first() -> None:
    nav: list[Any] = [
        {"Home": "index.md"},
        {"Install": ["install.md", {"On Kubernetes": [{"GKE": "gke.md"}]}]},
        "get-help.md",
        {"Reference": ["options.md"]},
        {"Archive": "https://example.com/archive/"},
    ]
    assert sections_from_nav(nav, "Overview") == {
        "Overview": ["index.md", "get-help.md"],
        "Install": ["install.md", "gke.md"],
        "Reference": ["options.md"],
    }


def test_a_page_is_listed_once_where_it_first_appears() -> None:
    nav: list[Any] = [
        {"Guide": ["a.md", "b.md", "a.md"]},
        {"Links": ["https://example.com/"]},
        {"Guide": ["c.md"]},
        {"Reference": ["b.md", "d.md"]},
    ]
    assert sections_from_nav(nav, "Start") == {"Guide": ["a.md", "b.md", "c.md"], "Reference": ["d.md"]}


def test_empty_nav() -> None:
    assert sections_from_nav([], "Overview") == {}
