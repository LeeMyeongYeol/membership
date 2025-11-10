import re
from typing import List, Dict, Any

HANGUL_BASE = 0xAC00
HANGUL_LAST = 0xD7A3
CHO = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
DBL = {'ㄲ':'ㄱ','ㄸ':'ㄷ','ㅃ':'ㅂ','ㅆ':'ㅅ','ㅉ':'ㅈ'}
RE_CHO_ONLY = re.compile(r'^[\u3131-\u314e]+$')

def is_choseong_only(s: str) -> bool:
    return bool(RE_CHO_ONLY.fullmatch(s or ""))

def get_choseong_char(ch: str):
    code = ord(ch)
    if code < HANGUL_BASE or code > HANGUL_LAST:
        return None
    return CHO[(code - HANGUL_BASE) // 588]

def to_choseong(s: str) -> str:
    out = []
    for ch in s or "":
        c = get_choseong_char(ch)
        if c:
            out.append(c)
        elif re.match(r'[A-Za-z0-9]', ch):
            out.append(ch.lower())
    return "".join(out)

def norm_cho(s: str) -> str:
    return re.sub(r'[ㄲㄸㅃㅆㅉ]', lambda m: DBL[m.group(0)], s or "")

def year_of(date_str: str) -> str:
    return (date_str or "")[:4]

def dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = {}
    for it in items:
        key = it.get("imdbID") or f"{(it.get('title') or '').lower()}_{it.get('year') or ''}"
        if key not in seen:
            seen[key] = it
    return list(seen.values())
