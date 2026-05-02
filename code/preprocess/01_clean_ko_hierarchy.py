
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Step 01: 한국어 전처리 + 토큰 분할 + 상·하위어 분리 → keywords_hierarchy_ko_clean.*
# 실행: python 01_clean_ko_hierarchy.py

import re, unicodedata, csv
import pandas as pd
from collections import Counter
from typing import List, Dict, Tuple

from path_config import (
    KO_HIERARCHY_CLEAN_CSV,
    KO_HIERARCHY_CLEAN_TSV,
    KO_HIERARCHY_CLEAN_UNQUOTED_CSV,
    KO_HIERARCHY_CLEAN_XLSX,
    METADATA_DIR,
    PROCESSED_DIR,
    RAW_DATA_CSV,
)

# ===== CONFIG =====
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

# ===== Utils =====
def normalize_unicode(s): return unicodedata.normalize("NFC", s)
def remove_zero_width(s): return s.replace("\u200b","").replace("\u2060","").replace("\ufeff","")
def strip_memo(s):
    # Remove editorial notes like "(새 라벨: ...)", "(New Label: ...)", or just "(새 라벨)"
    s = re.sub(r"\(\s*(?:새\s*라벨|New\s*Label)\s*[:：][^()]*\)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\(\s*(?:새\s*라벨|New\s*Label)\s*\)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰]+", "", s)
    s = re.sub(r"\[\s*\d+\s*\]", "", s)
    return s
def collapse_ws(s): return re.sub(r"\s+", " ", s).strip()
def balance_paren(s):
    oc, cc = s.count("("), s.count(")")
    changed = False
    if oc > cc:
        s += ")" * (oc-cc); changed = True
    elif cc > oc:
        for _ in range(cc-oc):
            i = s.rfind(")")
            if i != -1: s = s[:i] + s[i+1:]; changed = True
    return s, changed

def fix_ko_spaces(s: str) -> str:
    s2 = re.sub(r"([,/;|()+-])", r" \1 ", s)
    s2 = collapse_ws(s2)
    toks = s2.split(" ")
    def is_ko(t): return bool(re.fullmatch(r"[가-힣]+", t))
    out = []; i=0; n=len(toks)
    while i<n:
        if is_ko(toks[i]):
            seq=[]; j=i
            while j<n and is_ko(toks[j]): seq.append(toks[j]); j+=1
            if len(seq)>=2:
                lens=[len(t) for t in seq]
                if 1 in lens or (sum(lens)/len(lens) < 2.2):
                    out.append("".join(seq))
                else:
                    out.extend(seq)
            else:
                out.append(seq[0])
            i=j
        else:
            out.append(toks[i]); i+=1
    s3 = " ".join(out)
    s3 = re.sub(r"\s*([,/;|()+-])\s*", r"\1", s3)
    return collapse_ws(s3)

def clean_cell(text: str):
    s = normalize_unicode(str(text))
    s = remove_zero_width(s)
    s = strip_memo(s)
    # Remove markdown-like emphasis and footnote asterisks
    s = re.sub(r"\*+", "", s)  # '**bold**', '*' footnotes
    s = re.sub(r"__+", "", s)   # '__bold__'
    s = s.replace("`", "")       # inline code backticks
    s = collapse_ws(s)
    s = re.sub(r"\s*([,/;|+])\s*", r"\1", s)
    s = re.sub(r"\s*-\s*", "-", s)
    s2 = fix_ko_spaces(s)
    s = s2
    s2, _ = balance_paren(s)
    s = s2
    # Drop top-level parenthetical groups that contain no Korean (e.g., '(Sculpture)', '(CRISPR-Cas9)')
    def remove_en_only_top_level_parens(text: str) -> str:
        out_chars = []
        inner_buf = []
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

    s = remove_en_only_top_level_parens(s)
    s = re.sub(r"[,/;|+]+$", "", s).strip()
    return s

# ===== Hard-coded KO normalizations =====
def normalize_ko_term_label(label: str) -> str:
    """Apply project-specific KO term normalizations for base labels."""
    s = label
    # Spacing and lexical unification (base)
    s = re.sub(r"\b생태학적조립\b", "생태학적 조립", s)
    s = re.sub(r"\b데이터시각화\b", "데이터 시각화", s)
    s = re.sub(r"\b참여자협력\b", "참여자 협력", s)
    s = re.sub(r"\b미생물\s*연료\s*전지\b", "미생물 연료전지", s)
    s = re.sub(r"\b다중\s*감각적\s*경험\b", "다중감각적 경험", s)
    s = re.sub(r"\b웹\s*기반\s*프로젝트\b|\b웹기반프로젝트\b", "웹 기반 프로젝트", s)
    # Newly flagged terms
    s = re.sub(r"\b세포분화유도\b", "세포 분화 유도", s)
    s = re.sub(r"DNA\s*추출및전체유전체증폭", "DNA 추출 및 전체 유전체 증폭", s)
    s = re.sub(r"\b광유전학적자극\b", "광유전학적 자극", s)
    s = re.sub(r"\b데이터소리화\b", "데이터 소리화", s)
    s = re.sub(r"정동적경험의\s*창조", "정동적 경험의 창조", s)
    s = re.sub(r"RAL\s*표준색상시스템을이용한색재현", "RAL 표준 색상 시스템을 이용한 색 재현", s)
    s = re.sub(r"\b로봇제어시스템\b", "로봇 제어 시스템", s)
    s = re.sub(r"\b공생시스템구축\b", "공생 시스템 구축", s)
    s = re.sub(r"\b전통공예융합\b", "전통 공예 융합", s)
    s = re.sub(r"\b종간공동창작\b", "종간 공동 창작", s)
    s = re.sub(r"인간-기계협업", "인간-기계 협업", s)
    # AR&C specific fixes
    s = re.sub(r"\b사랑하는이\b", "사랑하는 이", s)
    s = re.sub(r"향기의원천", "향기의 원천", s)
    # '아카이브' variants (아카 이브, 아카이 브, 아카  이  브)
    s = re.sub(r"아카\s*이\s*브", "아카이브", s)
    s = re.sub(r"아카이\s*브", "아카이브", s)
    s = re.sub(r"아카\s*이브", "아카이브", s)
    s = re.sub(r"유전적주체공유", "유전적 주체 공유", s)
    s = re.sub(r"매개및기록자", "매개 및 기록자", s)
    s = re.sub(r"재료이자창조자", "재료이자 창조자", s)
    s = re.sub(r"생물학적물질", "생물학적 물질", s)
    s = re.sub(r"잠재적후손", "잠재적 후손", s)
    s = re.sub(r"사변적주체", "사변적 주체", s)
    s = re.sub(r"네트\s*워크", "네트워크", s)
    # Generic phrases frequently concatenated
    s = re.sub(r"프로세스및상호작용", "프로세스 및 상호작용", s)
    s = re.sub(r"성장및소멸", "성장 및 소멸", s)
    s = re.sub(r"과정및결과의사진기록", "과정 및 결과의 사진 기록", s)
    s = re.sub(r"디지털대생물학적기록방식에대한질문", "디지털 대생물학적 기록 방식에 대한 질문", s)
    s = re.sub(r"미래가족의형태에대한질문", "미래 가족의 형태에 대한 질문", s)
    s = re.sub(r"식품의기원에대한본능적대면을강요", "식품의 기원에 대한 본능적 대면을 강요", s)
    s = re.sub(r"기억에대한포스트휴먼적관점", "기억에 대한 포스트휴먼적 관점", s)
    s = re.sub(r"인간신체의신성성에대한질문", "인간 신체의 신성성에 대한 질문", s)
    s = re.sub(r"의식에대한유물론적관점", "의식에 대한 유물론적 관점", s)
    s = re.sub(r"식품의미래에대한사회적논쟁", "식품의 미래에 대한 사회적 논쟁", s)
    s = re.sub(r"사물에대한명상", "사물에 대한 명상", s)
    s = re.sub(r"가까운미래의시나리오를현재로소환", "가까운 미래의 시나리오를 현재로 소환", s)
    s = re.sub(r"과거의순간을포착하여미래를위해보존", "과거의 순간을 포착하여 미래를 위해 보존", s)
    s = re.sub(r"현재의친밀한순간을미래세대를위해기록", "현재의 친밀한 순간을 미래 세대를 위해 기록", s)
    s = re.sub(r"상호작용적설치물자체", "상호작용적 설치물 자체", s)
    # Newly reported Power & Capital Critique / Documentation fixes
    s = re.sub(r"인체로확장되는바이오자본주의", "인체로 확장되는 바이오 자본주의", s)
    s = re.sub(r"신경과학연구의펀딩구조와연구윤리", "신경과학 연구의 펀딩 구조와 연구 윤리", s)
    s = re.sub(r"비평텍스트를통한퍼포먼스기록", "비평 텍스트를 통한 퍼포먼스 기록", s)
    # Additional spacing fixes from review set
    s = re.sub(r"설치기록영상", "설치 기록 영상", s)
    s = re.sub(r"프로토타입전시", "프로토타입 전시", s)
    s = re.sub(r"프로젝트설명문", "프로젝트 설명문", s)
    s = re.sub(r"권력관계폭로", "권력 관계 폭로", s)
    s = re.sub(r"예술시장비판", "예술 시장 비판", s)
    s = re.sub(r"실시간프로세스\s*및\s*상호작용|실시간프로세스및상호작용", "실시간 프로세스 및 상호작용", s)
    s = re.sub(r"감각적피드백루프", "감각적 피드백 루프", s)
    s = re.sub(r"상호작용을통한능동적참여", "상호작용을 통한 능동적 참여", s)
    s = re.sub(r"담론적참여유도", "담론적 참여 유도", s)
    s = re.sub(r"서사적이해", "서사적 이해", s)
    s = re.sub(r"디지털시대의아날로그적경험추구", "디지털 시대의 아날로그적 경험 추구", s)
    s = re.sub(r"경험경제", "경험 경제", s)
    s = re.sub(r"뇌-컴퓨터인터페이스기술의발전", "뇌-컴퓨터 인터페이스 기술의 발전", s)
    s = re.sub(r"동물복지", "동물 복지", s)
    s = re.sub(r"지속가능한식량", "지속 가능한 식량", s)
    s = re.sub(r"발전하는생식기술", "발전하는 생식 기술", s)
    s = re.sub(r"소비자\s*직접유전학의부상|소비자직접유전학의부상", "소비자 직접 유전학의 부상", s)
    s = re.sub(r"새로운애도방식의탐구", "새로운 애도 방식의 탐구", s)
    s = re.sub(r"정신-신체이원론비판", "정신-신체 이원론 비판", s)
    s = re.sub(r"데이터화된자아탐구", "데이터화된 자아 탐구", s)
    s = re.sub(r"정신-신체이원론에도전", "정신-신체 이원론에 도전", s)
    s = re.sub(r"인지과정을외부화", "인지과정을 외부화", s)
    s = re.sub(r"데이\s*터", "데이터", s)
    s = re.sub(r"향기-기억-감정의연결성을가시화", "향기-기억-감정의 연결성을 가시화", s)
    s = re.sub(r"비-시각적감각의힘과정서적연결성을강조", "비-시각적 감각의 힘과 정서적 연결성을 강조", s)
    s = re.sub(r"비가\s*시적\s*화학\s*혼합물", "비가시적 화학 혼합물", s)
    s = re.sub(r"공업용화학물질", "공업용 화학물질", s)
    s = re.sub(r"샷건시퀀싱", "샷건 시퀀싱", s)
    s = re.sub(r"비-객체기반예술", "비-객체 기반 예술", s)
    s = re.sub(r"의도와통제", "의도와 통제", s)
    s = re.sub(r"자율적생물과정", "자율적 생물 과정", s)
    s = re.sub(r"자연-문화공동주도", "자연-문화 공동 주도", s)
    s = re.sub(r"돌봄기반", "돌봄 기반", s)
    s = re.sub(r"시적창조", "시적 창조", s)
    s = re.sub(r"단기전시", "단기 전시", s)
    s = re.sub(r"인간신체규모", "인간 신체 규모", s)
    s = re.sub(r"감정의영구보존과자연적소멸의대립", "감정의 영구 보존과 자연적 소멸의 대립", s)
    s = re.sub(r"유전정보의프라이버시", "유전 정보의 프라이버시", s)
    s = re.sub(r"사변적생식기술", "사변적 생식 기술", s)
    s = re.sub(r"자기-식인주의의경계", "자기-식인주의의 경계", s)
    s = re.sub(r"음식과자아의구분", "음식과 자아의 구분", s)
    s = re.sub(r"합성식품의의미", "합성 식품의 의미", s)
    s = re.sub(r"의식을만들고조작하는행위", "의식을 만들고 조작하는 행위", s)
    s = re.sub(r"향기의비자발적침투성", "향기의 비자발적 침투성", s)
    s = re.sub(r"생리적반응의유도", "생리적 반응의 유도", s)
    s = re.sub(r"불안을\s*유발하는|불안을유발하는", "불안을 유발하는", s)
    s = re.sub(r"내장\s*감각적|내장감각적", "내장 감각적", s)
    s = re.sub(r"요리의\s*형태|요리의형태", "요리의 형태", s)
    s = re.sub(r"미니멀\s*테크\s*미학|미니멀테크미학", "미니멀 테크 미학", s)
    s = re.sub(r"아카이브자료의관람", "아카이브 자료의 관람", s)
    s = re.sub(r"감정적반응유발", "감정적 반응 유발", s)
    s = re.sub(r"감시사회", "감시 사회", s)
    s = re.sub(r"식물의생애주기", "식물의 생애 주기", s)
    s = re.sub(r"지속과\s*소멸:\s*에너지를얻는한계속작동하지만", "지속과 소멸: 에너지를 얻는 한 계속 작동하지만", s)
    s = re.sub(r"언제든제거될수있는일시적생존의시간성", "언제든 제거될 수 있는 일시적 생존의 시간성", s)
    s = re.sub(r"식품산업비판", "식품 산업 비판", s)
    s = re.sub(r"동의없는유전정보사용", "동의 없는 유전 정보 사용", s)
    s = re.sub(r"신의영역침범", "신의 영역 침범", s)
    s = re.sub(r"실험실오브제", "실험실 오브제", s)
    s = re.sub(r"세포농업개념을구체화", "세포 농업 개념을 구체화", s)
    return collapse_ws(s)

DROP_MODIFIERS = {"내용상"}

def normalize_modifier_token(token: str) -> str:
    """Normalize individual modifier token by hard-coded rules."""
    s = token
    # Mirror base normalizations where semantically appropriate
    s = re.sub(r"\b생태학적조립\b", "생태학적 조립", s)
    s = re.sub(r"\b데이터시각화\b", "데이터 시각화", s)
    s = re.sub(r"\b참여자협력\b", "참여자 협력", s)
    s = re.sub(r"\b미생물\s*연료\s*전지\b", "미생물 연료전지", s)
    s = re.sub(r"\b다중\s*감각적\s*경험\b", "다중감각적 경험", s)
    s = re.sub(r"\b웹\s*기반\s*프로젝트\b|\b웹기반프로젝트\b", "웹 기반 프로젝트", s)
    s = re.sub(r"\b세포분화유도\b", "세포 분화 유도", s)
    s = re.sub(r"DNA\s*추출및전체유전체증폭", "DNA 추출 및 전체 유전체 증폭", s)
    s = re.sub(r"\b광유전학적자극\b", "광유전학적 자극", s)
    s = re.sub(r"\b데이터소리화\b", "데이터 소리화", s)
    s = re.sub(r"정동적경험의\s*창조", "정동적 경험의 창조", s)
    s = re.sub(r"RAL\s*표준색상시스템을이용한색재현", "RAL 표준 색상 시스템을 이용한 색 재현", s)
    s = re.sub(r"\b로봇제어시스템\b", "로봇 제어 시스템", s)
    s = re.sub(r"\b공생시스템구축\b", "공생 시스템 구축", s)
    s = re.sub(r"\b전통공예융합\b", "전통 공예 융합", s)
    s = re.sub(r"\b종간공동창작\b", "종간 공동 창작", s)
    s = re.sub(r"인간-기계협업", "인간-기계 협업", s)
    s = re.sub(r"\b사랑하는이\b", "사랑하는 이", s)
    s = re.sub(r"향기의원천", "향기의 원천", s)
    s = re.sub(r"아카\s*이\s*브", "아카이브", s)
    s = re.sub(r"아카이\s*브", "아카이브", s)
    s = re.sub(r"아카\s*이브", "아카이브", s)
    s = re.sub(r"유전적주체공유", "유전적 주체 공유", s)
    s = re.sub(r"매개및기록자", "매개 및 기록자", s)
    s = re.sub(r"재료이자창조자", "재료이자 창조자", s)
    s = re.sub(r"생물학적물질", "생물학적 물질", s)
    s = re.sub(r"잠재적후손", "잠재적 후손", s)
    s = re.sub(r"사변적주체", "사변적 주체", s)
    s = re.sub(r"네트\s*워크", "네트워크", s)
    s = re.sub(r"프로세스및상호작용", "프로세스 및 상호작용", s)
    s = re.sub(r"성장및소멸", "성장 및 소멸", s)
    s = re.sub(r"과정및결과의사진기록", "과정 및 결과의 사진 기록", s)
    s = re.sub(r"디지털대생물학적기록방식에대한질문", "디지털 대생물학적 기록 방식에 대한 질문", s)
    s = re.sub(r"미래가족의형태에대한질문", "미래 가족의 형태에 대한 질문", s)
    s = re.sub(r"식품의기원에대한본능적대면을강요", "식품의 기원에 대한 본능적 대면을 강요", s)
    s = re.sub(r"기억에대한포스트휴먼적관점", "기억에 대한 포스트휴먼적 관점", s)
    s = re.sub(r"인간신체의신성성에대한질문", "인간 신체의 신성성에 대한 질문", s)
    s = re.sub(r"의식에대한유물론적관점", "의식에 대한 유물론적 관점", s)
    s = re.sub(r"식품의미래에대한사회적논쟁", "식품의 미래에 대한 사회적 논쟁", s)
    s = re.sub(r"사물에대한명상", "사물에 대한 명상", s)
    s = re.sub(r"가까운미래의시나리오를현재로소환", "가까운 미래의 시나리오를 현재로 소환", s)
    s = re.sub(r"과거의순간을포착하여미래를위해보존", "과거의 순간을 포착하여 미래를 위해 보존", s)
    s = re.sub(r"현재의친밀한순간을미래세대를위해기록", "현재의 친밀한 순간을 미래 세대를 위해 기록", s)
    s = re.sub(r"상호작용적설치물자체", "상호작용적 설치물 자체", s)
    s = re.sub(r"인체로확장되는바이오자본주의", "인체로 확장되는 바이오 자본주의", s)
    s = re.sub(r"신경과학연구의펀딩구조와연구윤리", "신경과학 연구의 펀딩 구조와 연구 윤리", s)
    s = re.sub(r"비평텍스트를통한퍼포먼스기록", "비평 텍스트를 통한 퍼포먼스 기록", s)
    s = re.sub(r"설치기록영상", "설치 기록 영상", s)
    s = re.sub(r"프로토타입전시", "프로토타입 전시", s)
    s = re.sub(r"프로젝트설명문", "프로젝트 설명문", s)
    s = re.sub(r"권력관계폭로", "권력 관계 폭로", s)
    s = re.sub(r"예술시장비판", "예술 시장 비판", s)
    s = re.sub(r"실시간프로세스\s*및\s*상호작용|실시간프로세스및상호작용", "실시간 프로세스 및 상호작용", s)
    s = re.sub(r"감각적피드백루프", "감각적 피드백 루프", s)
    s = re.sub(r"상호작용을통한능동적참여", "상호작용을 통한 능동적 참여", s)
    s = re.sub(r"담론적참여유도", "담론적 참여 유도", s)
    s = re.sub(r"서사적이해", "서사적 이해", s)
    s = re.sub(r"디지털시대의아날로그적경험추구", "디지털 시대의 아날로그적 경험 추구", s)
    s = re.sub(r"경험경제", "경험 경제", s)
    s = re.sub(r"뇌-컴퓨터인터페이스기술의발전", "뇌-컴퓨터 인터페이스 기술의 발전", s)
    s = re.sub(r"동물복지", "동물 복지", s)
    s = re.sub(r"지속가능한식량", "지속 가능한 식량", s)
    s = re.sub(r"발전하는생식기술", "발전하는 생식 기술", s)
    s = re.sub(r"소비자\s*직접유전학의부상|소비자직접유전학의부상", "소비자 직접 유전학의 부상", s)
    s = re.sub(r"새로운애도방식의탐구", "새로운 애도 방식의 탐구", s)
    s = re.sub(r"정신-신체이원론비판", "정신-신체 이원론 비판", s)
    s = re.sub(r"데이터화된자아탐구", "데이터화된 자아 탐구", s)
    s = re.sub(r"정신-신체이원론에도전", "정신-신체 이원론에 도전", s)
    s = re.sub(r"데이\s*터", "데이터", s)
    s = re.sub(r"향기-기억-감정의연결성을가시화", "향기-기억-감정의 연결성을 가시화", s)
    s = re.sub(r"비-시각적감각의힘과정서적연결성을강조", "비-시각적 감각의 힘과 정서적 연결성을 강조", s)
    s = re.sub(r"비가\s*시적\s*화학\s*혼합물", "비가시적 화학 혼합물", s)
    s = re.sub(r"공업용화학물질", "공업용 화학물질", s)
    s = re.sub(r"샷건시퀀싱", "샷건 시퀀싱", s)
    s = re.sub(r"비-객체기반예술", "비-객체 기반 예술", s)
    s = re.sub(r"의도와통제", "의도와 통제", s)
    s = re.sub(r"자율적생물과정", "자율적 생물 과정", s)
    s = re.sub(r"자연-문화공동주도", "자연-문화 공동 주도", s)
    s = re.sub(r"돌봄기반", "돌봄 기반", s)
    s = re.sub(r"시적창조", "시적 창조", s)
    s = re.sub(r"감정의영구보존과자연적소멸의대립", "감정의 영구 보존과 자연적 소멸의 대립", s)
    s = re.sub(r"유전정보의프라이버시", "유전 정보의 프라이버시", s)
    s = re.sub(r"사변적생식기술", "사변적 생식 기술", s)
    s = re.sub(r"자기-식인주의의경계", "자기-식인주의의 경계", s)
    s = re.sub(r"음식과자아의구분", "음식과 자아의 구분", s)
    s = re.sub(r"합성식품의의미", "합성 식품의 의미", s)
    s = re.sub(r"의식을만들고조작하는행위", "의식을 만들고 조작하는 행위", s)
    s = re.sub(r"향기의비자발적침투성", "향기의 비자발적 침투성", s)
    s = re.sub(r"생리적반응의유도", "생리적 반응의 유도", s)
    s = re.sub(r"미니멀테크미학", "미니멀 테크 미학", s)
    s = re.sub(r"아카이브자료의관람", "아카이브 자료의 관람", s)
    s = re.sub(r"감정적반응유발", "감정적 반응 유발", s)
    s = re.sub(r"감시사회", "감시 사회", s)
    s = re.sub(r"식물의생애주기", "식물의 생애 주기", s)
    s = re.sub(r"지속과\s*소멸:\s*에너지를얻는한계속작동하지만", "지속과 소멸: 에너지를 얻는 한 계속 작동하지만", s)
    s = re.sub(r"언제든제거될수있는일시적생존의시간성", "언제든 제거될 수 있는 일시적 생존의 시간성", s)
    s = re.sub(r"식품산업비판", "식품 산업 비판", s)
    s = re.sub(r"동의없는유전정보사용", "동의 없는 유전 정보 사용", s)
    s = re.sub(r"신의영역침범", "신의 영역 침범", s)
    s = re.sub(r"실험실오브제", "실험실 오브제", s)
    s = re.sub(r"세포농업개념을구체화", "세포 농업 개념을 구체화", s)
    return collapse_ws(s)

def split_top_level(text: str) -> list:
    parts, buf, depth = [], [], 0
    for ch in text:
        if ch == "(":
            depth += 1; buf.append(ch)
        elif ch == ")":
            depth = max(0, depth-1); buf.append(ch)
        elif ch in ",/;|+" and depth == 0:
            t = "".join(buf).strip()
            if t: parts.append(t)
            buf = []
        else:
            buf.append(ch)
    if buf:
        t = "".join(buf).strip()
        if t: parts.append(t)
    return parts

def parse_hierarchy(term: str) -> Dict:
    s = clean_cell(term)
    base = s
    mods: List[str] = []

    # Extract base (before first top-level '(') and collect all top-level parenthetical groups
    if "(" in s and ")" in s:
        depth = 0
        base_chars: List[str] = []
        current_inner: List[str] = []
        inners: List[str] = []
        just_closed_top: bool = False
        for ch in s:
            if ch == "(":
                if depth == 0:
                    # starting a new top-level group
                    current_inner = []
                    just_closed_top = False
                else:
                    current_inner.append(ch)
                depth += 1
            elif ch == ")":
                if depth > 0:
                    depth -= 1
                    if depth == 0:
                        inners.append(collapse_ws("".join(current_inner)))
                        current_inner = []
                        just_closed_top = True
                    else:
                        current_inner.append(ch)
            else:
                if depth == 0:
                    # If we just closed a top-level group and adjacent chars are Korean, insert a space seam
                    if just_closed_top and base_chars and re.match(r"[가-힣]", base_chars[-1]) and re.match(r"[가-힣]", ch):
                        base_chars.append(" ")
                    base_chars.append(ch)
                    just_closed_top = False
                else:
                    current_inner.append(ch)

        base = collapse_ws("".join(base_chars))
        tokens: List[str] = []
        for inner in inners:
            if not inner:
                continue
            for t in re.split(r"[,/;|+]", inner):
                t2 = collapse_ws(t)
                if t2:
                    tokens.append(t2)
        mods = tokens

    return {
        "full_label_raw": str(term).strip(),
        "base_label": base,
        "modifiers_ko": ", ".join(mods)
    }

# ===== Axis Helpers (ensure English axis labels) =====
def extract_axis_en(axis_name: str) -> str:
    """Return English-only axis label.
    - If the column header has a trailing parenthetical in English, use its inner text.
    - Otherwise map known Korean-only headers to English.
    """
    s = collapse_ws(str(axis_name))
    m = re.search(r"\(([^()]*)\)\s*$", s)
    if m:
        inner = collapse_ws(m.group(1))
        return inner
    # Fallback mappings for headers without parentheses
    ko_to_en_axis = {
        "권력 및 자본 비판": "Power and Capital Critique",
    }
    return ko_to_en_axis.get(s, s)

# ===== Run =====
raw = pd.read_csv(RAW_DATA_CSV, engine="python")
axis_cols = raw.columns[4:]
axis_en_map = {axis: extract_axis_en(axis) for axis in axis_cols}

records = []
for axis in axis_cols:
    for cell in raw[axis].dropna().astype(str):
        cleaned = clean_cell(cell)
        for tok in split_top_level(cleaned):
            parsed = parse_hierarchy(tok)
            parsed["axis"] = axis_en_map.get(axis, axis)
            # Apply KO normalizations
            parsed["base_label"] = normalize_ko_term_label(parsed["base_label"]) if parsed["base_label"] else parsed["base_label"]
            if parsed["modifiers_ko"]:
                mods = [m.strip() for m in parsed["modifiers_ko"].split(",") if m.strip()]
                mods = [normalize_modifier_token(m) for m in mods]
                mods = [m for m in mods if m and m not in DROP_MODIFIERS]
                parsed["modifiers_ko"] = ", ".join(mods)
            records.append(parsed)

hier = pd.DataFrame(records).drop_duplicates().reset_index(drop=True)
out_csv = KO_HIERARCHY_CLEAN_CSV
out_xlsx = KO_HIERARCHY_CLEAN_XLSX
out_tsv = KO_HIERARCHY_CLEAN_TSV
out_csv_noquote = KO_HIERARCHY_CLEAN_UNQUOTED_CSV
# Reorder columns without full_label_fixed
cols = [c for c in ["full_label_raw", "base_label", "modifiers_ko", "axis"] if c in hier.columns]
hier = hier[cols]
hier.to_csv(out_csv, index=False)
hier.to_excel(out_xlsx, index=False)
hier.to_csv(out_tsv, sep='\t', index=False)
# Optional: CSV without quote characters (commas escaped with \\)
hier.to_csv(out_csv_noquote, index=False, quoting=csv.QUOTE_NONE, escapechar='\\')
print("[01] Saved:", f"{out_csv} | {out_xlsx} | {out_tsv} | {out_csv_noquote}")
