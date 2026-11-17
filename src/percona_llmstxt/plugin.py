"""The ``percona-llmstxt`` MkDocs plugin.

It works with mkdocs-llmstxt (the ``llmstxt`` plugin), which writes llms.txt,
llms-full.txt and the markdown pages, and fills in what Percona's docs need:

* the sections of llms.txt, from ``nav``, so there is no second list of pages;
* ``base_url``, from ``site_url`` and the version mike is deploying, so every
  version branch links to its own pages without per-branch settings;
* a pre-processing step that keeps the labels of content tabs;
* a link to llms.txt at the top of every markdown page and, hidden, in every
  HTML page;
* ``data-markdown-ignore`` on the parts of the HTML that are for people only.

Anything set explicitly on the ``llmstxt`` plugin in mkdocs.yml is kept.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mkdocs.config import config_options as opts
from mkdocs.config.base import Config
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError
from mkdocs.plugins import BasePlugin, event_priority
from mkdocs.structure.files import Files
from mkdocs.structure.pages import Page

from percona_llmstxt import preprocess
from percona_llmstxt.html import add_hint, mark_human_only
from percona_llmstxt.nav import sections_from_nav

LLMSTXT = "llmstxt"
MIKE_VERSION = "MIKE_DOCS_VERSION"  # set by `mike deploy` for the build it runs


class PerconaLlmsTxtConfig(Config):  # type: ignore[no-untyped-call]  # MkDocs: untyped __init_subclass__
    """Options under ``percona-llmstxt:`` in mkdocs.yml."""

    first_section = opts.Type(str, default="Overview")
    """The llms.txt section for top-level pages that are not in a nav group."""

    hint = opts.Type(bool, default=True)
    """Add the hidden link to llms.txt to every HTML page."""


def base_url(site_url: str, version: str | None) -> str:
    """The URL the links in llms.txt start with, ending in ``/``.

    During ``mike deploy 9.7`` it is ``<site_url>9.7/``. mike's own plugin may
    already have added the version to ``site_url``; it is not added twice.
    """
    root = site_url.rstrip("/")
    if version and not root.endswith("/" + version):
        root += "/" + version
    return root + "/"


def directive(index_url: str) -> str:
    """The line that starts every markdown page."""
    return f"> For the complete documentation index, see [llms.txt]({index_url}).\n\n"


class PerconaLlmsTxtPlugin(BasePlugin[PerconaLlmsTxtConfig]):  # type: ignore[no-untyped-call]  # same
    """Fills in the ``llmstxt`` plugin's settings and adds the links to llms.txt."""

    def __init__(self) -> None:
        self.index_url = ""
        self.md_pages: list[str] = []

    @event_priority(50)  # before the llmstxt plugin reads its settings
    def on_config(self, config: MkDocsConfig) -> MkDocsConfig:
        llmstxt: BasePlugin[Any] | None = config.plugins.get(LLMSTXT)
        if llmstxt is None:
            raise PluginError("percona-llmstxt needs the llmstxt plugin (mkdocs-llmstxt) in 'plugins'")
        if not config.site_url:
            raise PluginError("percona-llmstxt needs 'site_url' to build the links in llms.txt")

        settings = llmstxt.config
        if not settings.sections:
            settings.sections = sections_from_nav(config.nav or [], self.config.first_section)
        if not settings.base_url:
            settings.base_url = base_url(config.site_url, os.environ.get(MIKE_VERSION))
        if not settings.preprocess:
            settings.preprocess = preprocess.__file__
            settings.autoclean = False  # preprocess() runs it after labelling the tabs

        self.index_url = settings.base_url.rstrip("/") + "/llms.txt"
        return config

    def on_files(self, files: Files, *, config: MkDocsConfig) -> Files:
        """Remember where llmstxt will write the markdown pages."""
        llmstxt: BasePlugin[Any] = config.plugins[LLMSTXT]
        wanted = {page for pages in llmstxt.config.sections.values() for page in pages}
        self.md_pages = [
            Path(file.dest_uri).with_suffix(".md").as_posix()
            for file in files.documentation_pages()
            if file.src_uri in wanted
        ]
        return files

    def on_post_page(self, output: str, *, page: Page, config: MkDocsConfig) -> str:
        output = mark_human_only(output)
        return add_hint(output, self.index_url) if self.config.hint else output

    @event_priority(-100)  # after llmstxt has written the markdown pages
    def on_post_build(self, *, config: MkDocsConfig) -> None:
        line = directive(self.index_url)
        site_dir = Path(config.site_dir)
        for name in self.md_pages:
            path = site_dir / name
            if path.is_file():
                path.write_text(line + path.read_text(encoding="utf-8"), encoding="utf-8")
