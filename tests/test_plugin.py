"""Tests for the percona-llmstxt plugin: real MkDocs builds of a small site."""

from __future__ import annotations

from pathlib import Path

import pytest
from mkdocs.commands.build import build
from mkdocs.config import load_config
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.exceptions import PluginError

from percona_llmstxt.plugin import MIKE_VERSION, PerconaLlmsTxtPlugin, base_url, directive

SITE_URL = "https://docs.example.com/product/"

NAV = """
nav:
  - Home: index.md
  - Guide:
      - Install: install.md
  - Release notes:
      - notes/1.0.md
  - Archive: https://example.com/archive/
"""

TABS_PAGE = """# Install

=== "With Helm"

    helm install

=== "With kubectl"

    kubectl apply
"""


def make_site(
    tmp_path: Path, *, llmstxt: str = "  - llmstxt:\n      sections: {}\n", percona: str = "  - percona-llmstxt\n"
) -> Path:
    """Write a small MkDocs project and return its config file."""
    docs = tmp_path / "docs"
    (docs / "notes").mkdir(parents=True)
    (docs / "index.md").write_text("# Home\n\nWelcome.\n", encoding="utf-8")
    (docs / "install.md").write_text(TABS_PAGE, encoding="utf-8")
    (docs / "notes" / "1.0.md").write_text("# Release 1.0\n\nFirst.\n", encoding="utf-8")
    (docs / "draft.md").write_text("# Draft\n\nNot in nav.\n", encoding="utf-8")
    config = tmp_path / "mkdocs.yml"
    config.write_text(
        f"""
site_name: Product
site_url: {SITE_URL}
use_directory_urls: false
markdown_extensions:
  - toc:
      permalink: true
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
{NAV}
plugins:
{llmstxt}{percona}""",
        encoding="utf-8",
    )
    return config


def run_build(config_file: Path) -> Path:
    config = load_config(str(config_file))
    build(config)
    return Path(config.site_dir)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def no_mike(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(MIKE_VERSION, raising=False)


# --- helpers -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("site_url", "version", "expected"),
    [
        ("https://d.com/p/", None, "https://d.com/p/"),
        ("https://d.com/p", "", "https://d.com/p/"),
        ("https://d.com/p/", "9.7", "https://d.com/p/9.7/"),
        ("https://d.com/p/9.7", "9.7", "https://d.com/p/9.7/"),  # mike's plugin already added it
        ("https://d.com/p/19.7/", "9.7", "https://d.com/p/19.7/9.7/"),
    ],
)
def test_base_url(site_url: str, version: str | None, expected: str) -> None:
    assert base_url(site_url, version) == expected


def test_directive() -> None:
    assert (
        directive("https://d.com/llms.txt")
        == "> For the complete documentation index, see [llms.txt](https://d.com/llms.txt).\n\n"
    )


# --- builds ------------------------------------------------------------------


def test_build_without_settings(tmp_path: Path) -> None:
    site = run_build(make_site(tmp_path))
    index_url = SITE_URL + "llms.txt"

    index = read(site / "llms.txt")
    assert "## Overview\n\n- [Home](https://docs.example.com/product/index.md)" in index
    assert "## Guide\n\n- [Install](https://docs.example.com/product/install.md)" in index
    assert "## Release notes\n\n- [Release 1.0](https://docs.example.com/product/notes/1.0.md)" in index
    assert "Draft" not in index
    assert "Archive" not in index

    for page in ("index.md", "install.md", "notes/1.0.md"):
        text = read(site / page)
        assert text.startswith(directive(index_url)), page
        assert text.count("For the complete documentation index") == 1, page
    assert not (site / "draft.md").exists()

    install_md = read(site / "install.md")
    assert "**With Helm**\n\nhelm install\n\n**With kubectl**\n\nkubectl apply\n" in install_md
    assert "¶" not in install_md

    install_html = read(site / "install.html")
    assert '<a data-markdown-ignore class="headerlink"' in install_html
    assert '<div data-markdown-ignore class="tabbed-labels' in install_html
    assert f'<a href="{index_url}" tabindex="-1">llms.txt</a>' in install_html
    assert install_html.count('class="agent-hint"') == 1


def test_build_under_mike_links_to_the_version_being_deployed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(MIKE_VERSION, "9.7")
    site = run_build(make_site(tmp_path))
    assert "(https://docs.example.com/product/9.7/install.md)" in read(site / "llms.txt")
    assert read(site / "install.md").startswith(directive("https://docs.example.com/product/9.7/llms.txt"))
    assert 'href="https://docs.example.com/product/9.7/llms.txt"' in read(site / "index.html")


def test_settings_in_mkdocs_yml_are_kept(tmp_path: Path) -> None:
    llmstxt = """  - llmstxt:
      base_url: https://docs.example.com/product/latest/
      sections:
        Only:
          - install.md
"""
    percona = """  - percona-llmstxt:
      hint: false
"""
    site = run_build(make_site(tmp_path, llmstxt=llmstxt, percona=percona))
    index = read(site / "llms.txt")
    assert "## Only\n\n- [Install](https://docs.example.com/product/latest/install.md)" in index
    assert "## Overview" not in index
    assert not (site / "index.md").exists()
    assert read(site / "install.md").startswith(directive("https://docs.example.com/product/latest/llms.txt"))
    assert "agent-hint" not in read(site / "install.html")


def test_first_section_name(tmp_path: Path) -> None:
    site = run_build(make_site(tmp_path, percona="  - percona-llmstxt:\n      first_section: Start here\n"))
    assert "## Start here\n\n- [Home]" in read(site / "llms.txt")


def test_a_custom_preprocess_is_kept_and_autoclean_left_on(tmp_path: Path) -> None:
    script = tmp_path / "mine.py"
    script.write_text("def preprocess(soup, output):\n    soup.insert(0, 'MINE ')\n", encoding="utf-8")
    llmstxt = f"  - llmstxt:\n      sections: {{}}\n      preprocess: {script.as_posix()}\n"
    site = run_build(make_site(tmp_path, llmstxt=llmstxt))
    text = read(site / "install.md")
    assert "MINE" in text
    assert "**With Helm**" not in text  # the tab labels went with the plugin's own clean-up


def test_needs_the_llmstxt_plugin(tmp_path: Path) -> None:
    config: MkDocsConfig = load_config(str(make_site(tmp_path, llmstxt="")))
    with pytest.raises(PluginError, match="needs the llmstxt plugin"):
        config.plugins["percona-llmstxt"].on_config(config)


def test_needs_site_url(tmp_path: Path) -> None:
    config_file = make_site(tmp_path)
    config_file.write_text(read(config_file).replace(f"site_url: {SITE_URL}\n", ""), encoding="utf-8")
    config: MkDocsConfig = load_config(str(config_file))
    with pytest.raises(PluginError, match="needs 'site_url'"):
        config.plugins["percona-llmstxt"].on_config(config)


def test_pages_llmstxt_did_not_write_are_skipped(tmp_path: Path) -> None:
    config: MkDocsConfig = load_config(str(make_site(tmp_path)))
    build(config)
    plugin = config.plugins["percona-llmstxt"]
    assert isinstance(plugin, PerconaLlmsTxtPlugin)
    plugin.md_pages.append("gone.md")
    plugin.on_post_build(config=config)
    assert not (Path(config.site_dir) / "gone.md").exists()
