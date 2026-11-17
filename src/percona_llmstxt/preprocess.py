"""Pre-processing for mkdocs-llmstxt, which the plugin sets as its ``preprocess``.

mkdocs-llmstxt's own clean-up drops the labels of content tabs, so the
markdown loses which block is "With Helm" and which is "With kubectl". This
writes each label in bold at the top of its block, then runs that clean-up.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag
from mkdocs_llmstxt import autoclean


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
    label_tabs(soup)
    autoclean(soup)
