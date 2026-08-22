#!/usr/bin/env python3
"""Replace mechanical quest dialogue with context-aware Korean lines.

The live BlockShip JSON is authoritative.  This script deliberately edits only
lines which the dialogue audit has identified as mechanical boilerplate, plus
two explicitly reviewed farm lines.  Choices, node names, quest ids, and all
non-boilerplate story lines are preserved.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path


BOILERPLATE = [
    re.compile(r"이번에 맡길 일은"),
    re.compile(r"해야 할 일은"),
    re.compile(r"이번에도 네 솜씨 믿어도"),
    re.compile(r"지난 도움 안 잊었"),
    re.compile(r"이 정도면 충분해"),
    re.compile(r"아직 기다리고 있"),
    re.compile(r"다 끝내고 다시 얘기하자"),
    re.compile(r"우선 이 일부터 천천히 익혀"),
    re.compile(r"이제 다음 일 생각해도 되겠"),
    re.compile(r"지금까지 맡긴 일은 다 끝났"),
    re.compile(r"먼저 .*까지 찾아가는 것부터"),
]


def plain(text: str) -> str:
    return re.sub(r"[&§].", "", text or "").strip()


def item_name(value: str, forage: dict[str, dict]) -> str:
    display = {
        "기억의연못": "기억의 연못",
        "심해협곡": "심해 협곡",
        "심해교단본부": "심해 교단 본부",
        "무명의성소": "무명의 성소",
        "교단의인장": "교단의 인장",
        "교단의제기": "교단의 제기",
        "교단의해도": "교단의 해도",
        "교단의표식": "교단의 표식",
        "바르칸의심연": "바르칸의 심연",
        "바르칸조각": "바르칸 조각",
        "심해어가면": "심해어 가면",
        "심해전왕의핵": "심해전왕의 핵",
        "물고기비늘": "물고기 비늘",
        "강화실": "강화 실",
        "낡은갈고리": "낡은 갈고리",
    }
    if value in display:
        return display[value]
    if value.startswith("작물_"):
        return "특수 " + value.removeprefix("작물_").replace("_", " ")
    if value in forage:
        return forage[value].get("name") or forage[value].get("displayName") or value
    return value.replace("_", " ").replace("barkan:", "")


def number(value: str) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def particle(word: str, ieul: bool = True) -> str:
    """Return 을/를 (or 이/가) from the final Hangul syllable."""
    if not word:
        return "을" if ieul else "이"
    ch = word[-1]
    if "가" <= ch <= "힣":
        has_batchim = (ord(ch) - ord("가")) % 28 != 0
    else:
        has_batchim = False
    if ieul:
        return "을" if has_batchim else "를"
    return "이" if has_batchim else "가"


def grade_phrase(value: str) -> str:
    if not value or value == "아무":
        return "등급 제한 없이"
    if "~" in value:
        lo, hi = value.split("~", 1)
        return f"{lo}부터 {hi}까지"
    return f"{value}등급 이상"


def fish_phrase(species: str, grade: str, count: str, size: str, method: str, freshness: str = "") -> str:
    who = "물고기" if species in ("아무", "any", "") else species
    if grade in ("", "아무", "any"):
        qualifier = ""
    elif "~" in grade:
        qualifier = f"{grade}등급 "
    else:
        qualifier = f"{grade}등급 이상 "
    fresh = f"신선도 {freshness} 이상인 " if freshness not in ("", "0") else ""
    size_text = f"이고 {size}cm 이상인 " if size not in ("", "0") else ""
    return f"{fresh}{qualifier}{size_text}{who} {number(count)}마리를 {method} 일"


def goal_phrase(raw: str, forage: dict[str, dict]) -> str:
    p = raw.split("|")
    verb = p[0]
    try:
        if verb == "fish":
            species = item_name(p[1], forage) if len(p) > 1 else "물고기"
            return fish_phrase(species, p[2] if len(p) > 2 else "아무", p[3] if len(p) > 3 else "1", p[4] if len(p) > 4 else "0", "낚는")
        if verb == "fish_fresh":
            species = item_name(p[1], forage) if len(p) > 1 else "물고기"
            freshness = p[5] if len(p) > 5 else "0"
            return fish_phrase(species, p[2] if len(p) > 2 else "아무", p[3] if len(p) > 3 else "1", p[4] if len(p) > 4 else "0", "표본으로 가져오는", freshness)
        if verb == "harpoon":
            species = item_name(p[1], forage) if len(p) > 1 else "물고기"
            return "작살로 " + fish_phrase(species, p[2] if len(p) > 2 else "아무", p[3] if len(p) > 3 else "1", p[4] if len(p) > 4 else "0", "잡는")
        if verb == "area":
            names = [item_name(x, forage) for x in p[1].split(",") if x]
            return f"{'·'.join(names)} 지역을 직접 확인하는 일"
        if verb == "visit":
            target = p[2] if len(p) > 2 and p[2] else p[1]
            return f"{target}{particle(target)} 찾아가는 일"
        if verb == "dogam":
            names = "·".join(item_name(x, forage) for x in p[1].split(","))
            return f"{names} 도감을 {number(p[2])}종까지 채우는 일"
        if verb == "sell":
            return f"물고기 {number(p[1])}마리를 판매하는 일"
        if verb == "money":
            return f"보유금 {number(p[1])}원을 마련하는 일"
        if verb == "earn":
            return f"이번 주에 {number(p[1])}원을 버는 일"
        if verb in {"material", "submitmat"}:
            action = "제출하는" if verb == "submitmat" else "모으는"
            target = "재료" if len(p) < 2 or p[1] in ("", "아무", "any") else item_name(p[1], forage)
            return f"{target} {number(p[2])}개를 {action} 일"
        if verb == "forage":
            return f"{item_name(p[1], forage)} {number(p[2])}개를 채집하는 일"
        if verb == "mine":
            return f"{item_name(p[1], forage)} {number(p[2])}개를 채굴하는 일"
        if verb == "harvest":
            target = item_name(p[1], forage)
            return f"{target}{particle(target)} {number(p[2])}번 수확하는 일"
        if verb == "farmland":
            return f"경작지 {number(p[1])}칸을 만드는 일"
        if verb == "craft":
            target = p[1] if len(p) > 1 and p[1] else "제작품"
            if target in ("", "아무", "any"):
                return f"조합 {number(p[2])}회 하는 일"
            return f"{item_name(target, forage)} {number(p[2])}개를 제작하는 일"
        if verb == "deliver":
            target = item_name(p[1], forage)
            return f"{target}{particle(target)} {number(p[2])}개 전달하는 일"
        if verb == "eatdish":
            target = item_name(p[1], forage)
            return f"{target}{particle(target)} 먹는 일"
        if verb == "equip":
            target = p[1].replace('_', ' ')
            return f"{target}{particle(target)} 장착하는 일"
        if verb == "enhance":
            return f"장비를 {number(p[1])}회 강화하는 일"
        if verb == "skill":
            return f"스킬에 {number(p[1])}회 투자하는 일"
        if verb == "level":
            return f"레벨 {number(p[1])}에 도달하는 일"
        if verb == "collectible":
            return f"수집품 {number(p[1])}개를 모으는 일"
        if verb == "trap":
            return f"통발 {number(p[1])}개를 설치하는 일"
        if verb == "sail":
            return f"배로 {number(p[1])}블록 항해하는 일"
        if verb == "islandvisit":
            return f"다른 섬을 {number(p[1])}번 방문하는 일"
        if verb == "guilddonate":
            return f"길드에 {number(p[1])}원을 기부하는 일"
        if verb == "action":
            actions = {
                "메뉴": "메뉴를 열어보는 일",
                "퀘스트": "퀘스트 목록을 열어보는 일",
                "도감": "도감을 열어보는 일",
            }
            return actions.get(p[1], f"{p[1].replace('_', ' ')} 동작을 수행하는 일")
        if verb == "usebait":
            return f"미끼를 {number(p[1])}회 사용하는 일"
        if verb == "iceboxbuy":
            return "아이스박스를 구매하는 일"
        if verb == "iceboxstore":
            return f"아이스박스에 물고기 {number(p[1])}마리를 보관하는 일"
        if verb == "casino":
            return f"카지노에서 {number(p[1])}회 참여하는 일"
        if verb == "login":
            return f"{number(p[1])}일 접속하는 일"
        if verb == "quest_daily":
            return f"일일 퀘스트 {number(p[1])}개를 끝내는 일"
        if verb == "submit":
            target = item_name(p[1], forage)
            return f"{target}{particle(target)} 제출하는 일"
    except (IndexError, ValueError):
        pass
    return plain(raw).replace("|", " ").replace("_", " ")


def objective(quest: dict, forage: dict[str, dict]) -> str:
    goals = [goal_phrase(x, forage) for x in quest.get("목표", [])]
    if not goals:
        return "부탁한 일을 마무리하는 일"
    if len(goals) == 1:
        return goals[0]
    if len(goals) == 2:
        return f"{goals[0]}과 {goals[1]}을 모두 마무리하는 일"
    return " · ".join(goals) + "을 모두 마무리하는 일"


def style(npc: str) -> str:
    if npc in {"조반니", "하르트무트", "나디아", "도란", "대사서", "마르코", "로베르토", "카림", "유세프", "종지기", "왕실요리장"}:
        return "formal_o"
    if npc in {"피노", "테클라", "레일라", "마르타", "대장간안내", "시장안내", "요리안내"}:
        return "polite"
    if any(x in npc for x in ["할아버지", "오스발트", "알비스", "세르간", "노인", "노파"]):
        return "elder"
    if any(x in npc for x in ["왕", "영주", "라이너", "대사관"]):
        return "authority"
    if any(x in npc for x in ["대사서", "필경사", "사관", "나디아", "테클라", "마르타", "베티나", "레일라", "이자벨라"]):
        return "polite"
    if any(x in npc for x in ["하르트무트", "동굴", "펠릭스", "크로", "압바스", "카림", "엔리코", "피노", "조반니", "마테오", "게르하르트"]):
        return "rough"
    return "friendly"


def replacements(kind: str, npc: str, goal: str) -> list[str]:
    s = style(npc)
    if kind == "accept":
        if s == "elder":
            return [f"먼저 {goal}을 부탁하마.", "자세한 조건은 의뢰 내용을 확인하고, 준비가 되면 시작하거라."]
        if s == "authority":
            return [f"그대에게 {goal}을 맡기겠다.", "조건을 확인한 뒤 지체 없이 착수하라."]
        if s == "formal_o":
            return [f"이번에는 {goal}을 부탁하오.", "조건을 확인하고 준비가 되면 시작하시오."]
        if s == "polite":
            return [f"이번에는 {goal}을 부탁드릴게요.", "조건을 확인하시고 준비가 되면 시작해 주세요."]
        if s == "rough":
            return [f"할 일은 간단해. {goal}야.", "준비됐으면 바로 움직여."]
        return [f"부탁 하나만 할게요. {goal}예요.", "내용을 확인하고 준비되면 시작해 주세요."]
    if kind == "progress":
        if s == "elder":
            return [f"아직 {goal}이 남았단다.", "마치거든 바로 돌아오너라."]
        if s == "authority":
            return [f"아직 {goal}을 끝내지 못했군.", "완료하면 보고하라."]
        if s == "formal_o":
            return [f"아직 {goal}이 남았소.", "마치면 내게 알려 주시오."]
        if s == "polite":
            return [f"아직 {goal}이 남아 있어요.", "마치시면 제게 알려 주세요."]
        if s == "rough":
            return [f"아직 {goal}을 못 끝냈군.", "끝나면 돌아와."]
        return [f"아직 {goal}이 남아 있어요.", "마치면 다시 이야기해요."]
    if kind == "complete":
        if s == "elder":
            return [f"{goal}을 끝냈구나. 수고 많았다.", "약속한 보상을 받아 가거라."]
        if s == "authority":
            return [f"{goal}을 완수했군. 기록해 두겠다.", "보상을 수령하라."]
        if s == "formal_o":
            return [f"{goal}을 마쳤소. 큰 도움이 됐소.", "약속한 보상을 받아 가시오."]
        if s == "polite":
            return [f"{goal}을 마치셨네요. 큰 도움이 됐어요.", "약속한 보상을 받아 가세요."]
        if s == "rough":
            return [f"{goal}을 끝냈군. 수고했어.", "보상 받아."]
        return [f"{goal}을 마쳤네요. 고마워요.", "약속한 보상을 챙겨 가세요."]
    if kind == "first":
        if s == "elder":
            return [f"처음 맡길 일은 {goal}이란다."]
        if s == "authority":
            return [f"첫 임무는 {goal}이다."]
        if s == "formal_o":
            return [f"처음 부탁드릴 일은 {goal}이오."]
        if s == "polite":
            return [f"처음 부탁드릴 일은 {goal}이에요."]
        if s == "rough":
            return [f"첫 일은 {goal}이야."]
        return [f"처음 부탁할 일은 {goal}이에요."]
    if s == "elder":
        return ["네가 맡은 일은 모두 끝났구나.", "이곳에 남긴 손길을 오래 기억하마."]
    if s == "authority":
        return ["맡긴 일은 모두 마무리됐다.", "그대의 공을 기록에 남기겠다."]
    if s == "formal_o":
        return ["맡긴 일은 모두 마무리됐소.", "도와주셔서 고맙소. 다음에 또 들르시오."]
    if s == "polite":
        return ["맡긴 일은 모두 마무리됐어요.", "도와주셔서 고마워요. 다음에 또 들러 주세요."]
    if s == "rough":
        return ["맡은 일은 전부 끝났군.", "다음에 또 들러."]
    return ["맡긴 일은 모두 끝났어요.", "도와줘서 고마워요. 다음에 또 들러 주세요."]


def is_boilerplate(line: str) -> bool:
    return any(p.search(plain(line)) for p in BOILERPLATE)


ITEM_CATCH_NAMES = {
    "녹슨열쇠": "녹슨 열쇠",
    "밀랍봉인문서": "밀랍 봉인 문서",
    "은빛목걸이": "은빛 목걸이",
    "상단화물꼬리표": "상단 화물 꼬리표",
    "낡은가족사진": "낡은 가족사진",
    "이끼낀유리병": "이끼 낀 유리병",
    "밀수꾼의전리품": "밀수꾼의 전리품",
    "빛바랜자수실패": "빛바랜 자수 실패",
    "교단의인장": "교단의 인장",
    "교단의제기": "교단의 제기",
    "교단의해도": "교단의 해도",
    "교단의표식": "교단의 표식",
    "은가락지": "은가락지",
}


def clean_reviewed_text(text: str, npc: str = "") -> str:
    """Small, deterministic copy edits found by the Korean-language audit."""
    if text.startswith("할 일은 간단해. ") and text.endswith("일."):
        text = text[:-1] + "이야."
    if text.startswith("부탁 하나만 할게요. ") and text.endswith("일."):
        text = text[:-1] + "이에요."
    formal_o = {"조반니", "하르트무트", "나디아", "도란", "대사서", "마르코", "로베르토", "카림", "유세프", "종지기", "왕실요리장"}
    polite = {"피노", "테클라", "레일라", "마르타", "대장간안내", "시장안내", "요리안내"}
    if npc in formal_o:
        text = text.replace("일이야.", "일이오.")
        text = text.replace("일이에요.", "일이오.")
        text = text.replace("부탁 하나만 할게요.", "부탁 하나 하겠소.")
        text = text.replace("부탁드릴게요.", "부탁하오.")
        text = text.replace("못 끝냈군.", "끝내지 못했소.")
        text = text.replace("일이 남아 있어요.", "일이 남아 있소.")
        text = text.replace("일이 남았어요.", "일이 남았소.")
        text = text.replace("드디어 끝내셨네요. 수고 많으셨어요.", "드디어 끝냈소. 수고 많았소.")
        text = text.replace("결과를 보니 약속한 일을 다 해내셨네요.", "결과를 보니 약속한 일을 다 해냈소.")
        text = text.replace("맡긴 일을 깔끔하게 마무리하셨네요.", "맡긴 일을 깔끔하게 마무리했소.")
        text = text.replace("보상 받으시고 잠시 쉬셔도 좋아요.", "보상을 받고 잠시 쉬어도 좋소.")
        text = text.replace("보상은 준비해 뒀어요. 받아 가세요.", "보상은 준비해 뒀소. 받아 가시오.")
        text = text.replace("이제 약속한 보상을 챙겨 가세요.", "이제 약속한 보상을 챙겨 가시오.")
        text = text.replace("마치면 다시 이야기해요.", "마치면 다시 이야기합시다.")
    elif npc in polite:
        text = text.replace("일이야.", "일이에요.")
        text = text.replace("못 끝냈군.", "끝내지 못했어요.")
        text = text.replace("끝냈군. 수고했어.", "끝냈어요. 수고 많았어요.")
    # Normalize the old first-pass formatting for size-constrained fish.
    text = re.sub(
        r"(\S+) (\d+)마리\(([^)]+)\), 크기 (\d+)cm 이상를 낚는 일",
        r"\3이고 \4cm 이상인 \1 \2마리를 낚는 일",
        text,
    )
    text = re.sub(
        r"작살로 아무 (\d+)마리\(([^)]+)\)",
        r"작살로 \2 물고기 \1마리",
        text,
    )
    text = re.sub(
        r"물고기 (\d+)마리\(([^)]+)\)",
        r"\2 물고기 \1마리",
        text,
    )
    text = re.sub(
        r"물고기 (\d+)마리, 크기 (\d+)cm 이상",
        r"\2cm 이상인 물고기 \1마리",
        text,
    )
    text = re.sub(
        r"(\S+) (\d+)마리, 크기 (\d+)cm 이상를 낚는 일",
        r"\3cm 이상인 \1 \2마리를 낚는 일",
        text,
    )
    text = re.sub(r"([A-Z])부터 ([A-Z])까지", r"\1~\2등급", text)
    text = re.sub(r"아무 (\d+)개", r"재료 \1개", text)
    text = re.sub(
        r"([가-힣A-Za-z ]+?)을\(를\)",
        lambda m: m.group(1).rstrip() + particle(m.group(1).rstrip()),
        text,
    )
    for old, new in ITEM_CATCH_NAMES.items():
        text = text.replace(old, new)
    for old, new in [
        ("D~C등급 이상", "D~C등급"),
        ("C~B등급 이상", "C~B등급"),
        ("레벨 3을 달성", "레벨 3에 도달"),
        ("낚시 레벨 40을 달성", "낚시 레벨 40에 도달"),
        ("당신이 남긴 흔적", "자네가 남긴 흔적"),
        ("당신, 왕실", "자네, 왕실"),
        ("당신 이름", "자네 이름"),
        ("당신을 알아본", "자네를 알아본"),
        ("당신이 쓰고", "자네가 쓰고"),
        ("당신은 그 가면", "자네는 그 가면"),
        ("당신 손에", "자네 손에"),
        ("제가 아니라 당신이 다음 사람에게", "제가 아니라, 다음 사람에게"),
        ("당신이 뭘 잡아 오는지도", "자네가 뭘 잡아 오는지도"),
        ("낚시광은 당신이오", "낚시광은 자네요"),
        ("당신이 따라다닙니다", "자네를 따라다닙니다"),
        ("당신을 따라다닙니다", "자네를 따라다닙니다"),
        ("당신이 둘을 먼저", "자네가 둘을 먼저"),
        ("당신을 시험합니다", "자네를 시험합니다"),
        ("당신을 봅니다. 정확히는", "자네를 봅니다. 정확히는"),
        ("당신이 쓴 얼굴", "자네가 쓴 얼굴"),
        ("당신이 벗어 둔 가면", "자네가 벗어 둔 가면"),
        ("그것이 당신을 오래 봅니다.", "그것은 자네를 오래 봅니다."),
        ("서버에서 가장 긴 일입니다. 몇 달을 각오하세요.", "이 기록은 가장 긴 의뢰입니다. 몇 달은 각오하세요."),
        ("바르칸 국왕를", "바르칸 국왕을"),
        ("길드장 하겐를", "길드장 하겐을"),
        ("심해협곡", "심해 협곡"),
        ("심해교단본부", "심해 교단 본부"),
        ("무명의성소", "무명의 성소"),
        ("심해어가면", "심해어 가면"),
        ("바르칸의심연", "바르칸의 심연"),
        ("바르칸조각", "바르칸 조각"),
        ("물고기비늘", "물고기 비늘"),
        ("강화실", "강화 실"),
        ("기억의연못", "기억의 연못"),
        ("사막 릴을(를)", "사막 릴을"),
        ("코르크 찌을(를)", "코르크 찌를"),
        ("빵을(를)", "빵을"),
        ("세이지생선구이을(를)", "세이지 생선구이를"),
        ("피시앤칩스을(를)", "피시 앤 칩스를"),
        ("트러플스튜을(를)", "트러플 스튜를"),
        ("흔한 밀이 아니야.", "흔한 밀이 아니라네."),
        ("그래서 이걸 주려는 거야.", "그래서 이걸 주려는 걸세."),
    ]:
        text = text.replace(old, new)
    # These are quest-only catch items, not fish with a biological count.
    for name in ITEM_CATCH_NAMES.values():
        text = re.sub(rf"{re.escape(name)}\s+1마리를\s+낚는", f"{name} 하나를 건져 올리는", text)
        text = re.sub(rf"{re.escape(name)}\s+1마리를\s+잡는", f"{name} 하나를 건져 올리는", text)
    if "이 정도면 충분" in text:
        s = style(npc)
        text = {
            "elder": "잘 해냈구나. 필요한 건 모두 갖춰졌단다.",
            "authority": "좋다. 필요한 조건은 모두 충족됐다.",
            "polite": "좋아요. 필요한 건 모두 갖춰졌어요.",
            "rough": "됐어. 필요한 건 다 모였군.",
            "friendly": "좋아요. 필요한 건 모두 모였어요.",
        }[s]
    return text


def update_node(node: dict, kind: str, npc: str, goal: str) -> int:
    lines = node.get("lines") or []
    indexes = [i for i, line in enumerate(lines) if is_boilerplate(line)]
    if not indexes:
        return 0
    if kind == "epilogue":
        new = replacements("epilogue", npc, goal)
    elif kind == "first":
        new = replacements("first", npc, goal)
    else:
        new = replacements(kind, npc, goal)
    # Keep authored context and replace only flagged lines. If there are more
    # flagged lines than templates, use the final template as a safe fallback.
    for position, idx in enumerate(indexes):
        lines[idx] = new[min(position, len(new) - 1)]
    node["lines"] = lines
    return len(indexes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    base = Path(args.dir)
    qdata = json.loads((base / "quests.json").read_text())
    quests = qdata["퀘스트"]
    dialogue_path = base / "dialogue.json"
    dialogue = json.loads(dialogue_path.read_text())
    forage_path = base / "forage-types.json"
    forage_data = json.loads(forage_path.read_text()) if forage_path.exists() else {}
    forage = forage_data.get("types", forage_data) if isinstance(forage_data, dict) else {}

    changed = 0
    changed_nodes = 0
    samples = []
    for npc, nodes in dialogue.items():
        for key, node in nodes.items():
            qid = key.split("/", 1)[1] if "/" in key else None
            if qid and qid in quests:
                if key.startswith("인사/"):
                    kind = "accept"
                elif key.startswith("진행중/"):
                    kind = "progress"
                elif key.startswith("퀘스트완료/"):
                    kind = "complete"
                else:
                    continue
                goal = objective(quests[qid], forage)
                count = update_node(node, kind, npc, goal)
            elif key == "첫만남":
                qids = [x for x in quests if x in (nodes.get("quests") or [])]
                # NPC quest assignment lives in npc.json, not dialogue.json;
                # use the first quest whose id appears in any assigned list.
                qids = []
                for other_nodes in dialogue.values():
                    if other_nodes is nodes:
                        continue
                count = 0
            elif key == "후일담":
                count = update_node(node, "epilogue", npc, "")
            else:
                continue
            if count:
                changed += count
                changed_nodes += 1
                if len(samples) < 12:
                    samples.append(f"{npc}/{key}: {node.get('lines')}")

    # The first-meeting quest id is resolved from npc.json, because the dialogue
    # file intentionally contains no NPC metadata.
    npc_path = base / "npc.json"
    npc_data = json.loads(npc_path.read_text())
    for npc, n in npc_data.get("npcs", {}).items():
        node = dialogue.get(npc, {}).get("첫만남")
        if not node:
            continue
        qids = [qid for qid in n.get("quests", []) if qid in quests]
        if not qids or not any(is_boilerplate(x) for x in node.get("lines", [])):
            continue
        count = update_node(node, "first", npc, objective(quests[qids[0]], forage))
        changed += count
        if count:
            changed_nodes += 1
            if len(samples) < 12:
                samples.append(f"{npc}/첫만남: {node.get('lines')}")

    # Explicitly reviewed lines called out in the audit request.
    oswald = dialogue.get("오스발트", {}).get("첫만남", {}).get("lines", [])
    for i, line in enumerate(oswald):
        if "물고기는 잡으면 없어져. 밭은 안 그래." in line:
            oswald[i] = "물고기는 건져 올린 만큼만 남지만, 밭은 자리를 내어주면 계절마다 다시 돌려준다네."
            changed += 1
            changed_nodes += 1
    q = quests.get("본사이드_마인팜01")
    if q:
        q["설명"] = [
            line.replace('오스발트: "물고기는 잡으면 없어져. 밭은 안 그래."',
                         '오스발트: "물고기는 건져 올린 만큼만 남지만, 밭은 자리를 내어주면 계절마다 다시 돌려준다네."')
            for line in q.get("설명", [])
        ]
    # Apply copy edits to authored text as well as the generated replacements.
    for npc, nodes in dialogue.items():
        for node in nodes.values():
            node["lines"] = [clean_reviewed_text(line, npc) for line in node.get("lines", [])]
    for q in quests.values():
        if isinstance(q, dict) and isinstance(q.get("설명"), list):
            q["설명"] = [clean_reviewed_text(line) for line in q["설명"]]
    casino_goal = {
        "카지노_슬롯01": "슬롯머신에서 같은 심볼 세 개를 세 번 띄우는 일",
        "카지노_타짜01": "블랙잭 테이블에서 다섯 번 이기는 일",
        "카지노_폐인01": "카지노에서 순수익 20,000원을 내는 일",
        "카지노_큰손01": "카지노에서 순수익 150,000원을 내는 일",
    }
    for npc, nodes in dialogue.items():
        for key, node in nodes.items():
            qid = key.rsplit("/", 1)[-1]
            if qid not in casino_goal:
                continue
            goal = casino_goal[qid]
            for i, line in enumerate(node.get("lines", [])):
                if not any(token in line for token in ("카지노순익", "블랙잭승", "슬롯트리플", "카지노에서")):
                    continue
                if key.startswith("인사/"):
                    node["lines"][i] = f"이번 부탁은 {goal}예요."
                elif key.startswith("진행중/"):
                    node["lines"][i] = f"아직 {goal}이 남아 있어요."
    q = quests.get("본섬08")
    if q:
        q["설명"] = [
            "&7이 섬을 깊이 읽으려면 강과 협곡, 항구의 기록을 함께 맞춰야 합니다.",
            "&f강·협곡·항구 도감 18종&7을 채우고, 물고기 &f12마리&7를 시장에 판매하세요.",
            "&8의뢰: &7하겐",
        ]
    # Map review: the desert is west of the spawn city on the live X axis.
    q = quests.get("본섬11")
    if q:
        q["설명"] = [
            "&7사막은 같은 바르칸 섬의 서쪽 끝.",
            "&7마을 서쪽에서 말이나 화물 철도를 타고",
            "&7사막 어귀의 사막마을로 향하세요.",
        ]
    q = quests.get("영주05")
    if q:
        q["설명"] = [
            "&7영주 식탁에 오를 &f55cm 이상인 물고기 한 마리&7를 올리세요.",
            "&7발데마르: \"…이 정도면 왕도가 보낸 조사관보다 낫겠군.\"",
            "&7\"서쪽 사막의 물이 줄고 있다. 가서 보고 오너라.\"",
            "&8칭찬은 없습니다. 다만 일이 맡겨집니다.",
        ]
    # These four descriptions used the word "신선도", but their live goals
    # have no quality threshold. Keep the data and prose truthful.
    no_quality = {
        "알비스01": "&fS등급 이상 물고기 6마리&7를 표본으로 가져오세요.",
        "심해10": "&fA등급 이상 물고기 6마리&7를 올리세요.",
        "상사이드_레일라04": "&fB등급 이상 물고기 5마리&7를 가져다주세요.",
        "왕도11b": "&fA등급이면서 40cm 이상인 물고기 8마리&7를 올리세요.",
    }
    for qid, replacement in no_quality.items():
        if qid in quests:
            desc = quests[qid].get("설명", [])
            if desc:
                desc[-1] = replacement
    q = quests.get("본섬05")
    if q:
        q["설명"] = [
            "&7세르간이 인정할 만한 &f물고기&7를 가져가세요.",
            "&f신선도 80 이상인 B등급 물고기 한 마리&7.",
            "&8의뢰: &7세르간",
        ]
    copy_edits = {
        "본섬03": [("&f D~C등급&7 물고기를 4마리 낚아 가세요.", "&fD~C등급 물고기 4마리&7를 낚아 가세요.")],
        "본섬04": [("&7&f25cm 이상&7으로 8마리 잡아보세요.", "&f25cm 이상인 물고기 8마리&7를 잡아보세요.")],
        "사막06": [("&fB등급 이상 40cm 이상&7으로 &f3마리&7 잡으세요.", "&f40cm 이상인 B등급 물고기 3마리&7를 잡으세요.")],
        "본사이드_세르간01": [("옛 동료는 40cm 이상 A등급 2마리를", "옛 동료는 &f40cm 이상인 A등급 물고기 2마리&7를")],
        "사사이드_할릴01": [("C등급 이상 30cm 이상 &f물고기&7를 3마리 잡으세요.", "&f30cm 이상인 C등급 물고기 3마리&7를 잡으세요.")],
        "본사이드_마리03": [("&750cm 이상 C등급 물고기를", "&750cm 이상인 C등급 물고기")],
        "사사이드_할릴04": [("&7&fB등급 이상&7 &f2마리&7 · &f150cm 이상&7&7를 채우세요.", "&7&f150cm 이상인 B등급 물고기 2마리&7를 채우세요.")],
        "사사이드_나디아04": [("&790cm 이상 A등급 물고기를", "&790cm 이상인 A등급 물고기")],
        "상사이드_마르코04": [("&7100cm 이상 B등급 물고기를", "&7100cm 이상인 B등급 물고기")],
        "배상단04": [("&7밤을 지새우며 &fB등급 이상 50cm 이상&7으로 &f8마리&7 올리세요.", "&7밤을 지새우며 &f50cm 이상인 B등급 물고기 8마리&7를 올리세요.")],
        "왕사이드_요리장02": [("&770cm 이상 B등급 3마리를 가져다주세요.", "&770cm 이상인 B등급 물고기 3마리를 가져다주세요.")],
        "왕사이드_요리장03": [("&7왕의 만찬. 85cm 이상 A등급 2마리로", "&7왕의 만찬. &f85cm 이상인 A등급 물고기 2마리&7로")],
        "왕사이드_견습생01": [("&fA등급 이상&7 &f3마리&7 · &f80cm 이상&7도 함께 필요합니다.", "&fA등급 이상이면서 80cm 이상인 물고기 3마리&7도 함께 필요합니다.")],
    }
    for qid, edits in copy_edits.items():
        if qid in quests:
            quests[qid]["설명"] = [
                next((line.replace(old, new) for old, new in edits if old in line), line)
                for line in quests[qid].get("설명", [])
            ]

    if not args.dry_run:
        backup = dialogue_path.with_suffix(".json.bak-quest-audit")
        if not backup.exists():
            shutil.copy2(dialogue_path, backup)
        qbackup = base / "quests.json.bak-quest-audit"
        if not qbackup.exists():
            shutil.copy2(base / "quests.json", qbackup)
        dialogue_path.write_text(json.dumps(dialogue, ensure_ascii=False, indent=2) + "\n")
        (base / "quests.json").write_text(json.dumps(qdata, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({"changed_lines": changed, "changed_nodes": changed_nodes, "dry_run": args.dry_run, "samples": samples}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
