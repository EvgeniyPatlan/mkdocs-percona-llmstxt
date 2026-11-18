# mkdocs-percona-llmstxt

An MkDocs plugin that makes Percona documentation sites easy for AI agents and assistants to read. It works together with [mkdocs-llmstxt](https://github.com/pawamoy/mkdocs-llmstxt), which writes the files, and fills in everything a Percona docs repo would otherwise have to configure and maintain by hand.

A site built with both plugins gets:

- **`llms.txt`**, an index of every page in `nav`, grouped by the top-level nav sections, with links to the markdown pages ([llms.txt proposal](https://llmstxt.org/)).
- **`llms-full.txt`**, all pages in one file (if `full_output` is set).
- **A markdown copy of every page** next to its HTML: `backups.html` and `backups.md`. Each starts with a link to `llms.txt`. Content tabs keep their labels: each block starts with its label in bold.
- **A link to `llms.txt` in every HTML page**, hidden on screen and from screen readers, and out of the tab order.
- **`data-markdown-ignore`** on the heading anchors (¶) and tab-label bars in the HTML. They are for people only; tools that compare a page's HTML with its markdown skip such elements.

Nothing changes for people reading the site.

## Use

Python 3.11 or later. Add to `requirements.txt`:

```
mkdocs-llmstxt>=0.5.1,<0.6
mkdocs-percona-llmstxt
```

The plugin sets some of mkdocs-llmstxt's settings, so it supports one minor version of it at a time.

Add both plugins to `mkdocs.yml` (or `mkdocs-base.yml`):

```yaml
plugins:
  llmstxt:
    full_output: llms-full.txt
    markdown_description: >-
      Each page below is also available as markdown. For the documentation
      of all Percona products, see https://docs.percona.com/llms.txt.
    sections: {}  # mkdocs-llmstxt requires the key; percona-llmstxt fills it from nav
  percona-llmstxt: {}
```

That's all. The links in `llms.txt` are built from `site_url`. A build without `site_url`, such as a PDF build that inherits the plugins from `mkdocs-base.yml`, is left as it is: no markdown pages and no changes to the HTML.

## What it fills in

On the `llmstxt` plugin, unless `mkdocs.yml` already sets it:

| Setting | Value |
|---|---|
| `sections` | When empty (`{}`): one section per top-level nav group, in nav order. Top-level pages outside a group go into a first section, "Overview". External links are skipped. A page added to `nav` shows up in `llms.txt` with no other change. Pages that are built but not in `nav`, such as old release notes, go into a last section, "Optional": other pages link to them, so they get a markdown copy too, and in `llms.txt` "Optional" is the section an agent may skip when it is short of context. |
| `base_url` | `site_url`, plus the version during `mike deploy`. `mike deploy 9.7` builds with `MIKE_DOCS_VERSION=9.7`, so `https://docs.percona.com/percona-server/` becomes `https://docs.percona.com/percona-server/9.7/`. Each version branch links to its own pages, with no per-branch settings. |
| `preprocess` | Keeps the labels of content tabs, then runs the plugin's usual clean-up (`autoclean` is turned off so that it does not run twice). |

## Options

```yaml
  percona-llmstxt:
    first_section: Overview  # section for top-level pages outside a nav group
    other_pages: Optional    # section for pages outside nav; '' leaves them out
    hint: true               # the hidden link to llms.txt in every HTML page
```

## Check a site

[AFDocs](https://agentdocsspec.com/) scores a site against the Agent-Friendly Documentation spec:

```
npx afdocs check https://docs.percona.com/percona-operator-for-postgresql/latest/ --format scorecard
```

## Develop

```
python -m pip install --require-hashes --no-deps -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation .
ruff check . && ruff format --check . && mypy && pytest
```

`requirements-dev.txt` pins the tools and their hashes. To update it, edit `requirements-dev.in` and follow the command at its top.

## License

Apache License 2.0.
