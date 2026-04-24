#!/usr/bin/env python3
"""Build docs/docs.json from a single EN source-of-truth plus a label glossary.

Inputs (EDIT THESE):
  - docs/docs.base.json        — top-level Mintlify metadata (colors, theme, logo, navbar, ...)
  - docs/nav.template.json     — the EN tab/group/page structure (paths WITHOUT locale prefix)
  - scripts/docs-nav-glossary.json — canonical translations for every tab/group label
  - docs/nav-overrides/{locale}.json — optional per-locale patches (exclude / replace / extend)

Output (DO NOT EDIT BY HAND):
  - docs/docs.json — fed straight to Mintlify

Design:
  Deterministic, no LLM. The nav structure is identical across locales by default;
  only labels translate (via glossary) and paths get locale-prefixed. Per-locale
  differences (e.g. a page removed for regional compliance) are declared in the
  override files and applied as a final patch step, keeping diffs auditable.
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASE_PATH = ROOT / "docs" / "docs.base.json"
TEMPLATE_PATH = ROOT / "docs" / "nav.template.json"
GLOSSARY_PATH = ROOT / "scripts" / "docs-nav-glossary.json"
OVERRIDES_DIR = ROOT / "docs" / "nav-overrides"
DEFAULT_OUT = ROOT / "docs" / "docs.json"

LOCALES = ["en", "zh", "ja", "ko", "de", "fr"]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def translate_label(label: str, locale: str, glossary: dict) -> str:
    if locale == "en":
        return label
    entry = glossary.get("labels", {}).get(label)
    if entry is None:
        raise KeyError(
            f"Missing glossary entry for label {label!r}. "
            f"Add it to {GLOSSARY_PATH.relative_to(ROOT)}."
        )
    tr = entry.get(locale)
    if tr is None:
        raise KeyError(
            f"Missing {locale!r} translation for label {label!r} in glossary."
        )
    return tr


def prefix_path(path: str, locale: str) -> str:
    return path if locale == "en" else f"{locale}/{path}"


def transform_pages(pages: list, locale: str, glossary: dict) -> list:
    out: list = []
    for page in pages:
        if isinstance(page, str):
            out.append(prefix_path(page, locale))
        elif isinstance(page, dict):
            nested = deepcopy(page)
            if "group" in nested:
                nested["group"] = translate_label(nested["group"], locale, glossary)
            if "pages" in nested:
                nested["pages"] = transform_pages(nested["pages"], locale, glossary)
            out.append(nested)
        else:
            out.append(page)
    return out


def transform_group(group: dict, locale: str, glossary: dict) -> dict:
    g = deepcopy(group)
    g["group"] = translate_label(g["group"], locale, glossary)
    if "pages" in g:
        g["pages"] = transform_pages(g["pages"], locale, glossary)
    # `openapi`, `icon`, `tag`, etc. pass through untouched.
    return g


def transform_tab(tab: dict, locale: str, glossary: dict) -> dict:
    t = deepcopy(tab)
    t["tab"] = translate_label(t["tab"], locale, glossary)
    t["groups"] = [transform_group(g, locale, glossary) for g in t.get("groups", [])]
    return t


# ---- Override application -------------------------------------------------


def _strip_locale_prefix(path: str, locale: str) -> str:
    if locale == "en":
        return path
    lp = f"{locale}/"
    return path[len(lp):] if path.startswith(lp) else path


def _apply_exclude(group: dict, excludes: set[str], locale: str) -> None:
    if "pages" not in group:
        return
    kept: list = []
    for page in group["pages"]:
        if isinstance(page, str):
            en_form = _strip_locale_prefix(page, locale)
            if en_form in excludes:
                continue
            kept.append(page)
        elif isinstance(page, dict):
            _apply_exclude(page, excludes, locale)
            # drop nested groups that became empty
            if page.get("pages") or page.get("openapi"):
                kept.append(page)
        else:
            kept.append(page)
    group["pages"] = kept


def _apply_replace(group: dict, replacements: dict[str, str], locale: str) -> None:
    if "pages" not in group:
        return
    new_pages: list = []
    for page in group["pages"]:
        if isinstance(page, str):
            en_form = _strip_locale_prefix(page, locale)
            if en_form in replacements:
                new_pages.append(prefix_path(replacements[en_form], locale))
            else:
                new_pages.append(page)
        elif isinstance(page, dict):
            _apply_replace(page, replacements, locale)
            new_pages.append(page)
        else:
            new_pages.append(page)
    group["pages"] = new_pages


def apply_overrides(
    tabs: list, override: dict, locale: str, glossary: dict
) -> list:
    excludes = set(override.get("exclude") or [])
    replacements = override.get("replace") or {}
    extensions = override.get("extend") or []

    if excludes or replacements:
        for tab in tabs:
            for group in tab.get("groups", []):
                if excludes:
                    _apply_exclude(group, excludes, locale)
                if replacements:
                    _apply_replace(group, replacements, locale)

    # `extend`: list of {"tab": str, "group": str, "pages": [...]} — appends into a group
    for ext in extensions:
        tab_label = ext.get("tab")
        group_label = ext.get("group")
        extra_pages = ext.get("pages", [])
        target_tab = None
        for tab in tabs:
            if tab.get("tab") == translate_label(tab_label, locale, glossary):
                target_tab = tab
                break
        if target_tab is None:
            raise KeyError(
                f"override.extend: tab {tab_label!r} not found for locale {locale!r}"
            )
        target_group = None
        translated_group_label = translate_label(group_label, locale, glossary)
        for group in target_tab.get("groups", []):
            if group.get("group") == translated_group_label:
                target_group = group
                break
        if target_group is None:
            # create new group
            target_group = {"group": translated_group_label, "pages": []}
            target_tab.setdefault("groups", []).append(target_group)
        target_group.setdefault("pages", []).extend(
            prefix_path(p, locale) if isinstance(p, str) else p
            for p in extra_pages
        )

    # Prune any tab whose groups are all empty (no pages AND no openapi)
    pruned_tabs: list = []
    for tab in tabs:
        kept_groups = [
            g for g in tab.get("groups", [])
            if g.get("pages") or g.get("openapi")
        ]
        if kept_groups:
            tab["groups"] = kept_groups
            pruned_tabs.append(tab)
    return pruned_tabs


# ---- Top-level build ------------------------------------------------------


def build_language_block(
    template: dict, locale: str, glossary: dict, override: dict
) -> dict:
    tabs = [transform_tab(tab, locale, glossary) for tab in template["tabs"]]
    tabs = apply_overrides(tabs, override, locale, glossary)
    return {"tabs": tabs, "language": locale}


def load_override(locale: str) -> dict:
    path = OVERRIDES_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    data = load_json(path)
    # Strip comment key(s); accept any top-level key starting with '_'.
    return {k: v for k, v in data.items() if not k.startswith("_")}


def build(out_path: Path) -> None:
    base = load_json(BASE_PATH)
    template = load_json(TEMPLATE_PATH)
    glossary = load_json(GLOSSARY_PATH)

    languages = []
    for locale in LOCALES:
        override = {} if locale == "en" else load_override(locale)
        languages.append(build_language_block(template, locale, glossary, override))

    output = deepcopy(base)
    output["navigation"] = {"languages": languages}

    # Write with a trailing newline and preserved Unicode for readability.
    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    resolved = out_path.resolve()
    try:
        display = resolved.relative_to(ROOT)
    except ValueError:
        display = resolved
    print(f"build-docs-nav: wrote {display} ({len(languages)} locales)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output path (default: {DEFAULT_OUT.relative_to(ROOT)})",
    )
    args = parser.parse_args()
    try:
        build(args.out)
    except KeyError as e:
        print(f"build-docs-nav: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
