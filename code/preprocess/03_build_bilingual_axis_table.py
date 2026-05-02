#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import re
import csv
import unicodedata as ud
from typing import List, Tuple, Dict, Optional
import pandas as pd

from path_config import (
    BIOARTLAS_AXES_BILINGUAL_CSV as OUT_CSV,
    KO_EN_REVIEWED_CSV as MAP_CSV,
    QA_REPORTS_DIR as QA_DIR,
    RAW_DATA_CSV as DATA_IN,
    UNMAPPED_AXIS_TERMS_CSV as QA_UNMAPPED,
)

OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
QA_DIR.mkdir(parents=True, exist_ok=True)

# Known axis English names used in mapping CSV
AXIS_EN_ALLOWED = {
    "Materiality",
    "Methodology",
    "Actor Relationships & Configuration",
    "Ethical Approach",
    "Aesthetic Strategy",
    "Epistemic Function",
    "Philosophical Stance",
    "Social Context",
    "Audience Engagement",
    "Temporal Scale",
    "Spatio Scale",
    "Power and Capital Critique",
    "Documentation & Representation",
}

# Fallback header-ko -> header-en when English isn't present in parentheses
AXIS_HEADER_FALLBACK = {
    "권력 및 자본 비판": "Power and Capital Critique",
}


def nfc(s: str) -> str:
    return ud.normalize("NFC", s)


def strip_zw(s: str) -> str:
    # remove zero-width chars
    return re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", s)


def collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def clean_token(s: str) -> str:
    # Normalize and coerce NaN/None to empty string
    try:
        import pandas as pd  # local import safe
        if s is None or (isinstance(s, float) and pd.isna(s)):
            return ""
    except Exception:
        if s is None:
            return ""
    # common 'nan' string case from str(NaN)
    s_str = str(s)
    if s_str.strip().lower() == "nan":
        return ""
    return collapse_ws(strip_zw(nfc(s_str)))


def remove_en_only_top_level_parens(text: str) -> str:
    """Mimic 01's behavior: remove top-level () groups that contain no Korean chars."""
    if not isinstance(text, str):
        return text
    out_chars: List[str] = []
    inner_buf: List[str] = []
    depth = 0
    for ch in text:
        if ch == '(':
            if depth == 0:
                inner_buf = []
            else:
                inner_buf.append(ch)
            depth += 1
        elif ch == ')':
            if depth > 0:
                depth -= 1
                if depth == 0:
                    inner = collapse_ws("".join(inner_buf))
                    if re.search(r"[가-힣]", inner):
                        out_chars.append("(" + inner + ")")
                    inner_buf = []
                else:
                    inner_buf.append(ch)
            else:
                out_chars.append(ch)
        else:
            if depth == 0:
                out_chars.append(ch)
            else:
                inner_buf.append(ch)
    return collapse_ws("".join(out_chars))


def canonicalize_mods(mods_ko: str) -> str:
    if not isinstance(mods_ko, str) or not mods_ko.strip():
        return ""
    toks = [collapse_ws(t) for t in mods_ko.split(',') if collapse_ws(t)]
    toks_sorted = sorted(toks)
    return ", ".join(toks_sorted)


def extract_en_axis_from_header(header: str) -> Optional[str]:
    """Extract English axis name from a header like '물질성 (Materiality)'.
    If no parentheses present, try fallback map. Return None if unknown.
    """
    if not isinstance(header, str):
        return None
    m = re.search(r"\(([^)]+)\)", header)
    if m:
        return m.group(1).strip()
    # no parentheses → fallback
    return AXIS_HEADER_FALLBACK.get(header.strip())


def split_top_level(text: str) -> List[str]:
    """Split by comma/semicolon at top level, ignoring commas/semicolons inside parentheses."""
    if not isinstance(text, str) or text.strip() == "" or text.strip().lower() == "nan":
        return []
    out: List[str] = []
    buf: List[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch in ",;" and depth == 0:
            token = "".join(buf).strip()
            if token:
                out.append(token)
            buf = []
        else:
            buf.append(ch)
    # last token
    last = "".join(buf).strip()
    if last:
        out.append(last)
    return [clean_token(t) for t in out if clean_token(t)]


def parse_base_and_modifiers(token: str) -> Tuple[str, List[str]]:
    """Return Korean base_label and a list of modifiers_ko from a token like '동물(토끼, 개)'"""
    s = clean_token(token)
    if "(" not in s:
        return s, []
    # only consider top-level first '(' ... last ')'
    depth = 0
    base_chars: List[str] = []
    mods_chars: List[str] = []
    seen_paren = False
    for ch in s:
        if ch == "(":
            depth += 1
            if not seen_paren:
                seen_paren = True
                continue
        if ch == ")":
            depth = max(0, depth - 1)
            if depth == 0:
                continue
        if not seen_paren:
            base_chars.append(ch)
        else:
            mods_chars.append(ch)
    base = clean_token("".join(base_chars))
    mods_raw = clean_token("".join(mods_chars))
    if not mods_raw:
        return base, []
    # split modifiers by comma, top-level (no nested parens expected inside modifiers list)
    mods = [t.strip() for t in re.split(r",", mods_raw) if t.strip()]
    return base, mods


def _ko_no_space(text: str) -> str:
    """Remove all whitespaces from a token to tolerate spacing differences."""
    return re.sub(r"\s+", "", text or "")


def build_mapping_indexes(map_df: pd.DataFrame) -> Tuple[
    Dict[str, pd.Series],
    Dict[Tuple[str, str], pd.Series],
    Dict[str, pd.Series],
    Dict[Tuple[str, str], pd.Series],
    Dict[str, pd.Series],
    Dict[Tuple[str, str], pd.Series],
]:
    """
    Returns three dictionaries for mapping:
      - full_raw_map: full_label_raw -> row
      - struct_map: (base_label, normalized_modifiers_ko) -> row
      - base_map: base_label -> first matching row
    normalized_modifiers_ko: comma-joined normalized tokens
    """
    full_raw_map: Dict[str, pd.Series] = {}
    struct_map: Dict[Tuple[str, str], pd.Series] = {}
    base_map: Dict[str, pd.Series] = {}
    struct_map_ns: Dict[Tuple[str, str], pd.Series] = {}
    struct_map_sorted: Dict[Tuple[str, str], pd.Series] = {}
    base_map_ns: Dict[str, pd.Series] = {}

    for _, r in map_df.iterrows():
        full_raw = clean_token(r.get("full_label_raw", ""))
        base_ko = clean_token(r.get("base_label", ""))
        mods_ko = clean_token(r.get("modifiers_ko", ""))
        if full_raw:
            full_raw_map[full_raw] = r
        # normalize modifiers order/spacing as-is; we keep string to exact-match first
        key_struct = (base_ko, mods_ko)
        struct_map[key_struct] = r
        # no-space tolerant keys
        key_struct_ns = (_ko_no_space(base_ko), _ko_no_space(mods_ko))
        struct_map_ns[key_struct_ns] = r
        # order-insensitive (sorted) key
        key_struct_sorted = (base_ko, canonicalize_mods(mods_ko))
        struct_map_sorted[key_struct_sorted] = r
        if base_ko and base_ko not in base_map:
            base_map[base_ko] = r
        bns = _ko_no_space(base_ko)
        if bns and bns not in base_map_ns:
            base_map_ns[bns] = r
    return full_raw_map, struct_map, base_map, struct_map_ns, base_map_ns, struct_map_sorted


def to_en_label(row: pd.Series) -> str:
    base_en = clean_token(row.get("base_label_en", ""))
    mods_en = clean_token(row.get("modifiers_en", ""))
    axis_en = clean_token(row.get("axis", ""))

    # style normalization (hyphen/room-sized etc.) prior to Pascalization
    s_base = base_en
    s_mods = mods_en
    s_base = re.sub(r"\b[Ll]arge\s*scale\b", "large-scale", s_base)
    s_base = re.sub(r"\b[Rr]oom[- ]?size[d]?\b", "room-sized", s_base)
    s_mods = re.sub(r"\b[Ll]arge\s*scale\b", "large-scale", s_mods)
    s_mods = re.sub(r"\b[Rr]oom[- ]?size[d]?\b", "room-sized", s_mods)
    s_mods = re.sub(r"\bAudiovisual\b", "audiovisual", s_mods)

    # Convert to Pascal words but KEEP spaces (and keep punctuation like commas/parentheses)
    def _pascalize_word(core: str) -> str:
        if not core:
            return core
        if any(ch.isalpha() for ch in core):
            if core.isupper():
                return core
            if core[0].isdigit():
                return core
            return core[0].upper() + core[1:].lower()
        return core

    def _pascalize_token_keep_punct(tok: str) -> str:
        import re as _re
        m = _re.match(r"^([A-Za-z0-9\-]+)(.*)$", tok)
        if not m:
            return tok
        core, tail = m.group(1), m.group(2)
        # handle hyphenated words: Pascalize each part, keep hyphen
        parts = core.split('-')
        core_pas = '-'.join(_pascalize_word(p) for p in parts if p != '')
        return core_pas + tail

    def _to_pascal_with_spaces(text: str) -> str:
        import re as _re
        if not isinstance(text, str):
            return ""
        tokens = _re.findall(r"\s+|[^ \t\n\r\f\v]+", text)
        out = []
        for t in tokens:
            if t.isspace():
                out.append(" ")
            else:
                out.append(_pascalize_token_keep_punct(t))
        return collapse_ws("".join(out))

    base_pas = _to_pascal_with_spaces(s_base)
    mods_pas = ""
    if s_mods:
        # split modifiers by comma and pascalize each phrase, keep spaces inside
        parts = [t.strip() for t in s_mods.split(',') if t.strip()]
        mods_pas = ", ".join(_to_pascal_with_spaces(p) for p in parts)

    if mods_pas:
        return f"{base_pas} ({mods_pas})"
    return base_pas


def to_ko_label(row: pd.Series) -> str:
    base_ko = clean_token(row.get("base_label", ""))
    mods_ko = clean_token(row.get("modifiers_ko", ""))
    if mods_ko:
        return f"{base_ko} ({mods_ko})"
    return base_ko


def map_token(
    token: str,
    axis_en: str,
    full_raw_map,
    struct_map,
    base_map,
    struct_map_ns,
    base_map_ns,
    struct_map_sorted,
    qa_list,
    row_id,
) -> Tuple[Optional[str], Optional[str]]:
    tok = clean_token(token)
    if not tok:
        return None, None
    # 1) direct full_label_raw match filtered by axis (if present)
    if tok in full_raw_map:
        r = full_raw_map[tok]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r), to_ko_label(r)
    # 1b) 01-like cleaned variant
    tok_like01 = remove_en_only_top_level_parens(tok)
    if tok_like01 in full_raw_map:
        r = full_raw_map[tok_like01]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r), to_ko_label(r)
    # 2) structured match base + modifiers string
    base_ko, mods_list = parse_base_and_modifiers(tok)
    mods_ko_str = ", ".join([clean_token(m) for m in mods_list])
    key = (base_ko, mods_ko_str)
    if key in struct_map:
        r = struct_map[key]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r), to_ko_label(r)
    # 2b) spacing-tolerant struct match
    key_ns = (_ko_no_space(base_ko), _ko_no_space(mods_ko_str))
    if key_ns in struct_map_ns:
        r = struct_map_ns[key_ns]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r), to_ko_label(r)
    # 2c) order-insensitive modifiers
    key_sorted = (base_ko, canonicalize_mods(mods_ko_str))
    if key_sorted in struct_map_sorted:
        r = struct_map_sorted[key_sorted]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r), to_ko_label(r)
    # 3) base-only fallback
    if base_ko in base_map:
        r = base_map[base_ko]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r), to_ko_label(r)
    # 3b) base-only spacing tolerant
    bns = _ko_no_space(base_ko)
    if bns in base_map_ns:
        r = base_map_ns[bns]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r), to_ko_label(r)
    # Unmapped → record
    qa_list.append({
        "row": row_id,
        "axis_en": axis_en,
        "original": token,
        "base_ko": base_ko,
        "mods_ko": mods_ko_str,
    })
    return None, None


def map_token_to_en(token: str, axis_en: str, full_raw_map, struct_map, base_map, struct_map_ns, base_map_ns, struct_map_sorted, qa_list, row_id) -> Optional[str]:
    tok = clean_token(token)
    if not tok:
        return None
    # 1) direct full_label_raw match filtered by axis (if present)
    if tok in full_raw_map:
        r = full_raw_map[tok]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r)
    # 1b) 01-like cleaned variant
    tok_like01 = remove_en_only_top_level_parens(tok)
    if tok_like01 in full_raw_map:
        r = full_raw_map[tok_like01]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r)
    # 2) structured match base + modifiers string
    base_ko, mods_list = parse_base_and_modifiers(tok)
    mods_ko_str = ", ".join([clean_token(m) for m in mods_list])
    key = (base_ko, mods_ko_str)
    if key in struct_map:
        r = struct_map[key]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r)
    # 2b) spacing-tolerant struct match
    key_ns = (_ko_no_space(base_ko), _ko_no_space(mods_ko_str))
    if key_ns in struct_map_ns:
        r = struct_map_ns[key_ns]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r)
    # 2c) order-insensitive modifiers
    key_sorted = (base_ko, canonicalize_mods(mods_ko_str))
    if key_sorted in struct_map_sorted:
        r = struct_map_sorted[key_sorted]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r)
    # 3) base-only fallback
    if base_ko in base_map:
        r = base_map[base_ko]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r)
    # 3b) base-only spacing tolerant
    bns = _ko_no_space(base_ko)
    if bns in base_map_ns:
        r = base_map_ns[bns]
        if not axis_en or clean_token(r.get("axis")) == axis_en:
            return to_en_label(r)
    # Unmapped → record
    qa_list.append({
        "row": row_id,
        "axis_en": axis_en,
        "original": token,
        "base_ko": base_ko,
        "mods_ko": mods_ko_str,
    })
    return None


def main():
    # Load mapping CSV
    mdf = pd.read_csv(MAP_CSV)
    # ensure expected columns exist
    required = {"full_label_raw", "base_label", "base_label_en", "modifiers_ko", "modifiers_en", "axis"}
    missing = list(required - set(mdf.columns))
    if missing:
        raise SystemExit(f"Missing columns in mapping file: {missing}")
    # Indexes
    full_raw_map, struct_map, base_map, struct_map_ns, base_map_ns, struct_map_sorted = build_mapping_indexes(mdf)

    # Load data.csv (keep as string)
    df = pd.read_csv(DATA_IN, dtype=str, keep_default_na=False)

    # Detect axis columns and build header mapping
    axis_headers_ko: List[str] = []
    axis_headers_en: List[str] = []
    for col in df.columns:
        en = extract_en_axis_from_header(col)
        if en:
            if en not in AXIS_EN_ALLOWED:
                # ignore columns with non-axis English
                pass
            else:
                axis_headers_ko.append(col)
                axis_headers_en.append(en)
        elif col in AXIS_HEADER_FALLBACK:
            en = AXIS_HEADER_FALLBACK[col]
            axis_headers_ko.append(col)
            axis_headers_en.append(en)
    if not axis_headers_ko:
        raise SystemExit("No axis columns detected from data.csv headers")

    # Build output DataFrame with identifier columns + English & Korean axis columns
    out_records: List[Dict[str, str]] = []
    qa_unmapped: List[Dict[str, str]] = []
    id_cols: List[str] = [c for c in ["Artist", "Artwork", "Year", "Gen"] if c in df.columns]
    axis_headers_ko_out: List[str] = [f"{en}_ko" for en in axis_headers_en]

    for ridx, row in df.iterrows():
        out_row: Dict[str, str] = {}
        # copy identifiers
        for ic in id_cols:
            out_row[ic] = clean_token(row.get(ic, ""))
        row_id = ridx + 1
        for col_ko, col_en in zip(axis_headers_ko, axis_headers_en):
            cell = row.get(col_ko, "")
            tokens = split_top_level(cell)
            mapped_en_list: List[str] = []
            mapped_ko_list: List[str] = []
            for tok in tokens:
                mapped_en, mapped_ko = map_token(
                    tok,
                    col_en,
                    full_raw_map,
                    struct_map,
                    base_map,
                    struct_map_ns,
                    base_map_ns,
                    struct_map_sorted,
                    qa_unmapped,
                    row_id,
                )
                if mapped_en:
                    mapped_en_list.append(mapped_en)
                if mapped_ko:
                    mapped_ko_list.append(mapped_ko)
            # de-duplicate while preserving order
            def _dedup(seq: List[str]) -> List[str]:
                s = set(); out: List[str] = []
                for t in seq:
                    if t not in s:
                        s.add(t); out.append(t)
                return out
            out_row[col_en] = ", ".join(_dedup(mapped_en_list))
            out_row[f"{col_en}_ko"] = ", ".join(_dedup(mapped_ko_list))
        out_records.append(out_row)

    out_df = pd.DataFrame(out_records, columns=id_cols + axis_headers_en + axis_headers_ko_out)
    out_df.to_csv(OUT_CSV, index=False)

    pd.DataFrame(qa_unmapped).to_csv(QA_UNMAPPED, index=False)

    print("[03] Saved:")
    print(" -", OUT_CSV)
    print(" -", QA_UNMAPPED)


if __name__ == "__main__":
    main()
