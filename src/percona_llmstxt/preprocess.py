"""Pre-processing for mkdocs-llmstxt, which the plugin sets as its ``preprocess``.

mkdocs-llmstxt's own clean-up drops the labels of content tabs, so the
markdown loses which block is "With Helm" and which is "With kubectl". This
writes each label in bold at the top of its block, points links at the
markdown copies of pages, then runs that clean-up.

mkdocs-llmstxt imports this file by path and calls ``preprocess`` only, so
what the plugin knows (where the site is built, which pages have a markdown
copy) is passed in with :func:`configure`. mkdocs-llmstxt runs this file as
a fresh copy of the module for every page, so ``preprocess`` reads that state
from the installed module, the one ``configure`` was called on.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path, PurePosixPath

from bs4 import BeautifulSoup, Tag
from mkdocs_llmstxt import autoclean

from percona_llmstxt.links import rewrite_links


@dataclass(frozen=True)
class _State:
    site_dir: str
    md_pages: frozenset[str]


_state: _State | None = None


def configure(site_dir: str, md_pages: frozenset[str]) -> None:
    """Tell ``preprocess`` where the site is built and which pages get a markdown copy."""
    global _state
    _state = _State(site_dir, md_pages)


def _classes(tag: Tag) -> list[str]:
    value = tag.get("class")
    return list(value) if isinstance(value, list) else []


def _children_with_class(tag: Tag, name: str) -> list[Tag]:
    return [child for child in tag.find_all(recursive=False) if name in _classes(child)]


def label_tabs(soup: BeautifulSoup) -> None:
    """Put each tab's label at the top of its block and drop the label bar."""
    for tab_set in soup.find_all(class_="tabbed-set"):
        label_bars = _children_with_class(tab_set, "tabbed-labels")
        contents = _children_with_class(tab_set, "tabbed-content")
        if len(label_bars) != 1 or len(contents) != 1:
            continue
        labels = label_bars[0].find_all("label", recursive=False)
        blocks = _children_with_class(contents[0], "tabbed-block")
        for label, block in zip(labels, blocks, strict=False):
            title = soup.new_tag("p")
            strong = soup.new_tag("strong")
            strong.string = label.get_text(" ", strip=True)
            title.append(strong)
            block.insert(0, title)
        label_bars[0].decompose()


def preprocess(soup: BeautifulSoup, output: str) -> None:
    """Called by mkdocs-llmstxt for every page before it becomes markdown."""
    state: _State | None = import_module("percona_llmstxt.preprocess")._state
    if state is not None:
        try:
            page_dir = PurePosixPath(Path(output).relative_to(state.site_dir).parent.as_posix())
        except ValueError:  # not a page of the configured site: leave its links alone
            pass
        else:
            rewrite_links(soup, "" if str(page_dir) == "." else str(page_dir), state.md_pages)
    label_tabs(soup)
    autoclean(soup)
