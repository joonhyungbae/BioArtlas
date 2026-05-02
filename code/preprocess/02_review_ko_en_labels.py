#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
02_review_ko_en_labels.py
- 한국어→영어 수동 번역 결과를 자동 교정(수정) + 요약 리포트 출력
- 입력: metadata/keywords_hierarchy_ko_en_review.csv
- 출력:
    - metadata/keywords_hierarchy_ko_en_reviewed.csv (교정본)
    - metadata/qa_reports/*.csv (선택: 참고용 리포트)
"""

import re
import pandas as pd

from path_config import KO_EN_REVIEWED_CSV as OUT_FIXED
from path_config import KO_HIERARCHY_REVIEW_CSV as IN_CSV
from path_config import QA_REPORTS_DIR as OUT_DIR

OUT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLS = [
    "full_label_raw", "base_label", "base_label_en",
    "modifiers_ko", "modifiers_en", "axis"
]

# 1) 사전 기반 의심 번역 패턴 (오역 가능성 높은 케이스)
SUSPECT_PATTERNS = [
    (r"\b굴\b", r"\boyster\b", "굴(oyster)"),
    (r"\b쪽\b", r"\bindigo\b", "쪽(indigo)"),
    (r"소변", r"\burine\b", "소변은 urine"),
    (r"데이터소리화|데이터 소리화", r"\bsonification\b", "Sonification 권장"),
    (r"^관객$", r"\baudience\b", "관객은 audience"),
    (r"가상", r"\bvirtual\b", "가상은 virtual"),
    (r"^향$|향분자", r"\b(odor|odorant|scent|fragrance molecules)\b", "incense 지양"),
    (r"탈멸종", r"\bde[- ]?extinction\b", "탈멸종은 de-extinction"),
]

# 2) 번역 누락 규칙
def has_text(x: str) -> bool:
    return isinstance(x, str) and x.strip() != ""

# 3) 스타일/표기 일관성 (하이픈/복수/케이스)
STYLE_CHECKS = [
    (r"\broom size[d]?\b", "room-sized 권장"),
    (r"\bLarge scale\b", "large-scale 권장"),
]

def explode_modifiers(row):
    ko_raw = row.get("modifiers_ko")
    en_raw = row.get("modifiers_en")
    ko_str = ko_raw if isinstance(ko_raw, str) else ""
    en_str = en_raw if isinstance(en_raw, str) else ""
    ko = [t.strip() for t in ko_str.split(",") if t.strip()]
    en = [t.strip() for t in en_str.split(",") if t.strip()]
    # 길이 불일치 시 페어링 유지 위해 채움
    m = max(len(ko), len(en))
    ko += [""] * (m - len(ko))
    en += [""] * (m - len(en))
    return list(zip(ko, en))

# ========== 교정 규칙 ==========
BASE_KO_TO_EN_FIX = {
    # base_label 기준 교정
    "관객": "Audience",
    "데이터소리화": "Sonification",
    "복합 조직체": "Composite organism",
    "조각": "Sculpture",
    "정동적 경험의 창조": "Creating affective experiences",
    "경계의 모호함": "Ambiguity of boundaries",
    "혐오의전복": "Subversion of the abject",
    "정동적": "Affective",
    "알고리즘적 재현": "Algorithmic representation",
    "대기적": "Ambient",
    "사랑하는 이": "Loved one",
    "미래제안& 사변적 디자인": "Future proposal & speculative design",
    "시각중심 주의비판": "Critique of ocularcentrism",
    "탈멸종": "De-extinction",
}

MOD_KO_TO_EN_FIX = {
    # modifiers 기준 교정 (KO 정확히 일치 시 적용)
    "굴": "oyster",
    "쪽": "indigo",
    "소변": "urine",
    "가상": "virtual",
    "향": "scent",
    "향분자": "fragrance molecules",
    "시청각": "audiovisual",
    "부분": "part",
    "갤러리 공간": "gallery space",
}

def style_normalize_en(text: str) -> str:
    if not isinstance(text, str):
        return text
    s = text
    # 하이픈/복합표기 통일
    s = re.sub(r"\b[Ll]arge\s*scale\b", "large-scale", s)
    s = re.sub(r"\b[Rr]oom[- ]?size[d]?\b", "room-sized", s)
    # 케이스 일관성 (보수적 소문자화)
    s = re.sub(r"\bAudiovisual\b", "audiovisual", s)
    s = re.sub(r"\bGallery space\b", "gallery space", s)
    # 불필요 대문자/케이스는 보수적 유지
    return s

def fix_base_pair(base_ko: str, base_en: str) -> str:
    if isinstance(base_ko, str) and base_ko in BASE_KO_TO_EN_FIX:
        return BASE_KO_TO_EN_FIX[base_ko]
    # 데이터 소리화 변형 대응
    if isinstance(base_ko, str) and re.search(r"데이터\s*소리화|데이터소리화", base_ko):
        return "Sonification"
    # 공백 변형 대응 규칙들
    if isinstance(base_ko, str):
        # 정동적 경험의 창조 (공백 유무)
        if re.fullmatch(r"정동적\s*경험의\s*창조", base_ko):
            return "Creating affective experiences"
        # 시각중심주의 비판(오타/공백)
        if re.fullmatch(r"시각중심\s*주의\s*비판|시각중심주의\s*비판", base_ko):
            return "Critique of ocularcentrism"
    return base_en

def fix_mod_pair(ko: str, en: str) -> str:
    if isinstance(ko, str) and ko in MOD_KO_TO_EN_FIX:
        return MOD_KO_TO_EN_FIX[ko]
    # 향 케이스: incense -> scent로 교체
    if isinstance(ko, str) and re.fullmatch(r"향", ko or "") and isinstance(en, str) and re.search(r"incense", en, re.I):
        return "scent"
    # Sonification 잔여
    if isinstance(ko, str) and re.search(r"데이터\s*소리화|데이터소리화", ko) and isinstance(en, str) and not re.search(r"sonification", en, re.I):
        return "Sonification"
    return en

def main():
    df = pd.read_csv(IN_CSV)
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        raise SystemExit(f"Missing columns: {missing_cols}")

    suspects = []
    missing = []
    style_issues = []

    # 교정본 프레임
    fixed = df.copy()

    for idx, row in df.iterrows():
        full_raw = row.get("full_label_raw", "")
        base_ko = row.get("base_label", "")
        base_en = row.get("base_label_en", "")

        # 누락: KO가 있으면 EN도 있어야 함
        if has_text(base_ko) and not has_text(base_en):
            missing.append({
                "row": idx+1, "field": "base_label_en",
                "base_label": base_ko, "suggest": ""
            })
        # base 교정 적용
        new_base_en = fix_base_pair(base_ko, base_en)
        new_base_en = style_normalize_en(new_base_en)
        fixed.at[idx, "base_label_en"] = new_base_en

        # 수식어 페어 검사 + 교정
        mod_pairs = explode_modifiers(row)
        new_mod_ens = []
        for ko, en in mod_pairs:
            if has_text(ko) and not has_text(en):
                missing.append({
                    "row": idx+1, "field": "modifiers_en",
                    "ko": ko, "suggest": ""
                })
            fixed_en = fix_mod_pair(ko, en)
            fixed_en = style_normalize_en(fixed_en)
            new_mod_ens.append(fixed_en or "")

            # 의심 번역 패턴 검사
            # 의심 번역 패턴 검사
            for ko_pat, en_pat, note in SUSPECT_PATTERNS:
                if re.search(ko_pat, ko or "") and has_text(fixed_en) and not re.search(en_pat, fixed_en, flags=re.IGNORECASE):
                    suspects.append({
                        "row": idx+1,
                        "full_label_raw": full_raw,
                        "ko": ko,
                        "en": fixed_en,
                        "rule": f"{ko_pat} !~ {en_pat}",
                        "note": note
                    })
        # 교정된 modifiers_en 반영
        fixed.at[idx, "modifiers_en"] = ", ".join([t for t in new_mod_ens if t])

        # base-level 의심 번역도 검사 (예: 관객 → Audience)
        for ko_pat, en_pat, note in SUSPECT_PATTERNS:
            if re.search(ko_pat, base_ko) and has_text(base_en) and not re.search(en_pat, base_en, flags=re.IGNORECASE):
                suspects.append({
                    "row": idx+1,
                    "full_label_raw": full_raw,
                    "ko": base_ko,
                    "en": base_en,
                    "rule": f"{ko_pat} !~ {en_pat}",
                    "note": note
                })

        # 스타일 체크 (영문만 대상)
        for pat, note in STYLE_CHECKS:
            current_mod_en_str = row.get("modifiers_en") if isinstance(row.get("modifiers_en"), str) else ""
            for target in filter(has_text, [new_base_en] + [t.strip() for t in current_mod_en_str.split(",")]):
                if re.search(pat, target):
                    style_issues.append({
                        "row": idx+1,
                        "full_label_raw": full_raw,
                        "text": target,
                        "note": note
                    })

    # 교정본 저장
    fixed.to_csv(OUT_FIXED, index=False)
    pd.DataFrame(suspects).to_csv(OUT_DIR / "en_suspects.csv", index=False)
    pd.DataFrame(missing).to_csv(OUT_DIR / "en_missing.csv", index=False)
    pd.DataFrame(style_issues).to_csv(OUT_DIR / "en_style_issues.csv", index=False)

    print("[02] Reports saved:")
    for fn in ["en_suspects.csv", "en_missing.csv", "en_style_issues.csv"]:
        print(" -", OUT_DIR / fn)
    print("[02] Fixed saved:", OUT_FIXED)

if __name__ == "__main__":
    main()
