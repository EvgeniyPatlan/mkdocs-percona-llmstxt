"""Turn an MkDocs ``nav`` into the sections of llms.txt."""

from __future__ import annotations

from typing import Any


def nav_pages(item: Any) -> list[str]:
    """Return the ``.md`` files in a nav item, in nav order. Links are skipped."""
    if isinstance(item, str):
        return [item] if item.endswith(".md") else []
    if isinstance(item, dict):
        return [page for value in item.values() for page in nav_pages(value)]
    if isinstance(item, list):
        return [page for value in item for page in nav_pages(value)]
    return []


def sections_from_nav(nav: list[Any], first_section: str) -> dict[str, list[str]]:
    """Map each top-level nav group to its pages.

    Top-level pages that are not in a group go into ``first_section``, which
    comes first. A page listed twice is kept where it first appears, and
    groups with no pages (only external links) are left out.
    """
    sections: dict[str, list[str]] = {first_section: []}
    for item in nav:
        if isinstance(item, dict) and len(item) == 1:
            title, value = next(iter(item.items()))
            if isinstance(value, list):
                sections.setdefault(title, []).extend(nav_pages(value))
                continue
        sections[first_section].extend(nav_pages(item))

    seen: set[str] = set()
    result: dict[str, list[str]] = {}
    for title, pages in sections.items():
        unique = [page for page in dict.fromkeys(pages) if page not in seen]
        seen.update(unique)
        if unique:
            result[title] = unique
    return result
