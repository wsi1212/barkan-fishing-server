#!/usr/bin/env python3
"""Add authored follow-up lines to short, displayable NPC dialogue.

Functional NPCs are intentionally not included: NpcInteractListener opens their
GUI before the dialogue engine, so a dialogue set there would never be shown.
This patch appends lines to existing nodes and restores the missing final
``후일담`` node for five quest NPCs. It does not add quests or NPCs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


# Each value is an authored continuation for the existing node.  Keeping the
# map explicit makes reruns idempotent and prevents accidental changes to quest
# dialogue or functional NPCs.
ADDITIONS: dict[str, dict[str, list[str]]] = {
    "위병3": {
        "인사": ["종탑 쪽은 사람들 발길이 잦소. 길 한가운데 서 있지는 마시오."],
    },
    "위병4": {
        "인사": ["봉인된 서고 쪽 문은 허가받은 사람만 드나드오. 호기심은 잠시 접어 두시오."],
    },
    "시민1": {
        "인사": ["이번에는 왕립 대도서관 안쪽까지 들어가 보고 싶소. 바깥에서 듣는 이야기만으로는 아쉽거든."],
    },
    "시민2": {
        "인사": ["상단에서 들여온 향신료가 오늘 아침에 다 나갔소. 왕도 사람들은 새 물건을 참 좋아한다니까."],
    },
    "시민3": {
        "인사": ["도서관 앞 광장은 해 질 무렵이면 더 붐벼요. 길을 건널 땐 수레부터 살피세요."],
    },
    "시민4": {
        "인사": ["필사실은 아무나 들어갈 수 없대요. 그래도 언젠가는 제 이름으로 책 한 장을 베껴 보고 싶어요."],
    },
    "시민5": {
        "인사": ["종지기님은 바람에 흔들린 등불이라지만, 사흘째 같은 시각에 켜진다니까요."],
    },
    "시민6": {
        "인사": ["오늘 들어온 생선은 어디서 왔는지 장부에 먼저 적는다더군요. 왕도에선 물길도 기록하는 모양이에요."],
    },
    "안토니오": {
        "인사": ["상단마을 창고는 밤에도 문을 닫을 틈이 없지. 물건이 많다고 좋은 것만은 아니오."],
    },
    "줄리아": {
        "인사": ["장부에서 빠진 숫자 하나가 마을 전체를 흔들기도 해요. 그래서 두 번씩 세고 있답니다."],
    },
    "프란체스코": {
        "인사": ["상단마을 바다는 잔잔해 보여도 물살이 다르지. 배를 띄울 땐 육지보다 바람을 먼저 보게."],
    },
    "클라우디아": {
        "인사": ["향신료는 비린내를 덮는 게 아니라 살짝 눌러 주는 거예요. 생선마다 어울리는 향도 다르답니다."],
    },
    "빈센초": {
        "인사": ["낯선 손님이 오면 술보다 먼저 이야기를 묻지. 어느 항구를 거쳤는지 알아야 잔도 맞춰 따르거든."],
    },
    "살바토레": {
        "인사": ["새 그물은 물을 먹기 전엔 가볍지만, 큰 놈이 걸리면 손목부터 버텨야 해."],
    },
    "로사": {
        "인사": ["좋은 생선은 눈부터 맑아요. 냄새만 맡고 고르다간 낭패를 보죠."],
    },
    "마시모": {
        "인사": ["한 가지 좋은 점은 있지. 부두에선 배가 돌아오는 소리를 제일 먼저 듣는다네."],
    },
    "잔니": {
        "인사": ["나무판 사이로 물이 스미는 소리는 금방 알아. 늦게 손보면 배 한 척이 통째로 고생이지."],
    },
    "베아트리체": {
        "인사": ["부두에서 올라오는 바람을 기준으로 삼으면 길을 찾기 쉬워요. 골목이 비슷해 보여도 방향은 거짓말을 안 하거든요."],
    },
    "도메니코": {
        "인사": ["바다를 오래 떠난 사람은 육지에서도 파도에 맞춰 걷는다네. 나도 아직 버릇을 못 고쳤지."],
    },
    "하인리히": {
        "인사": ["요즘은 젊은 낚시꾼들이 더 멀리 나가더군. 그래도 강가 물결은 오래 본 사람이 읽는 법이지."],
    },
    "그레첸": {
        "인사": ["빵은 식기 전에 먹어야 제맛이지만, 멀리 가져갈 거라면 천으로 감싸야 해요."],
    },
    "볼프강": {
        "인사": ["목재는 젖은 채로 세우면 나중에 꼭 뒤틀려. 급해도 말릴 건 말려야지."],
    },
    "잉가": {
        "인사": ["이 우물은 오래 써도 물맛이 변하지 않아요. 필요한 만큼만 길어 가면 모두가 오래 쓸 수 있답니다."],
    },
    "디르크": {
        "인사": ["배가 늦는 날엔 사람들이 부두부터 탓하지만, 물때가 꼬인 날은 누구도 서두를 수 없죠."],
    },
    "헬무트": {
        "인사": ["가루가 곱다고 빵이 저절로 맛있어지는 건 아니에요. 물 온도와 반죽 시간이 더 중요하죠."],
    },
    "라시드4": {
        "인사": ["여관을 지나치면 골목 끝에서 길이 갈리오. 밤에는 표지판을 잘 보시오."],
    },
    "아미라": {
        "인사": ["낮에는 모래가 모든 발자국을 삼키지만, 밤이면 별이 길을 다시 그려 준답니다."],
    },
    "군나르": {
        "인사": ["파도가 잦아들어도 계류줄은 한 번 더 확인하는 법이오. 항구에선 방심한 배가 먼저 떠내려가니까."],
    },
    "페더": {
        "인사": ["손가락에 난 굳은살이 그물 상태를 알려 주지. 눈으로 보는 것보다 빠르거든."],
    },
    "랄프": {
        "인사": ["가끔은 빈손으로 돌아오는 배도 있지. 그럴 때는 짐보다 사람 얼굴부터 살핀다오."],
    },
    "미아": {
        "인사": ["칼날이 무디면 살을 망치고, 너무 날카로우면 손을 망쳐요. 손질은 서두르면 안 돼요."],
    },
    "레오": {
        "인사": ["갈매기한테 빼앗기기 전에 머리 위부터 살피세요. 저 녀석들, 사람이 만만해 보이면 꼭 내려옵니다!"],
    },
    "프리다": {
        "인사": ["항구에서 듣는 노래는 멀리 퍼져야 제맛이에요. 파도 소리가 박자를 좀 틀려도 괜찮고요."],
    },
    "발터": {
        "인사": ["불빛을 낮게 걸어 두면 멀리서도 배가 방향을 잡지. 밤바다에선 어둠보다 신호 하나가 더 중요하오."],
    },
    "인트로선장": {
        "인사": ["멀미가 나면 수평선을 보게. 물결보다 배 안쪽을 바라보는 게 더 고역이거든."],
    },
    "인트로갑판원": {
        "인사": ["난간 밖으로 몸을 내밀지 마십시오. 바다는 가까이서 볼수록 발을 잡아당깁니다."],
    },
    "인트로취사": {
        "인사": ["배가 흔들릴 때 국물을 가득 담아 달라는 건 손님이지. 조금 모자라게 담아야 갑판까지 무사히 갑니다."],
    },
    "인트로돛담당": {
        "인사": ["돛줄은 젖으면 무거워진다. 도착할 때까지 손에서 놓지 마라."],
    },
    "일곱셋": {
        "진행중/심사이드_일곱셋01": ["이름 하나면 된다. 없는 것보단 낫다."],
    },
    "가라앉은하": {
        "진행중/심사이드_하01": ["수조의 물은 이미 식었다. 그래도 약속은 남아 있다."],
    },
}


EPILOGUES = {
    "모르": {
        "lines": [
            "…이제 부탁할 것은 없다.",
            "네가 다녀간 뒤로, 여기 것들의 이름을 하나씩 불러 줄 수 있게 됐다.",
            "위로 갈 수는 없어도, 잊히지는 않겠지.",
        ],
        "choices": [{"id": "c1", "text": "다음에 또 오겠습니다", "action": "닫기", "next": "x"}],
    },
    "비늘짜는이": {
        "lines": [
            "이제 손을 멈춰도 되겠다.",
            "네가 가져온 것들은 버려진 채로 남지 않았다.",
            "다음에 오거든, 조용히 앉아 있어라. 실을 잇는 데는 말보다 시간이 필요하다.",
        ],
        "choices": [{"id": "c1", "text": "다음에 또 오겠습니다", "action": "닫기", "next": "x"}],
    },
    "일곱셋": {
        "lines": [
            "…이름. 이제 있다.",
            "나. 일곱-셋 아니다. 그렇게 부르면 돌아본다.",
            "너. 또 오면, 이름 불러 준다.",
        ],
        "choices": [{"id": "c1", "text": "다음에 또 올게요", "action": "닫기", "next": "x"}],
    },
    "가라앉은하": {
        "lines": [
            "…이제 값은 다 치렀다.",
            "안쪽을 묻는 자가 오면, 나는 다시 말하겠다.",
            "너는 돌아와도 된다.",
        ],
        "choices": [{"id": "c1", "text": "다음에 또 오겠습니다", "action": "닫기", "next": "x"}],
    },
    "오스발트": {
        "lines": [
            "이제 맡길 밭일은 없네.",
            "자네 섬은 자네 손으로 일구는 곳이야. 나는 가끔 흙 냄새나 맡으러 오겠네.",
            "물가에만 붙어 있던 젊은것이, 제법 땅을 보는 눈을 얻었구먼.",
        ],
        "choices": [{"id": "c1", "text": "다음에 또 들를게요", "action": "닫기", "next": "x"}],
    },
}


REMOVE_LINES = {
    "종탑 쪽은 수레가 자주 드나드니, 길 한가운데 서 있지는 마시오.",
    "그래도 부두에서 일하면 배가 돌아오는 소리를 제일 먼저 듣는다네. 그건 좀 괜찮지.",
    "이 우물은 오래 써도 물맛이 흐려지지 않아요. 필요한 만큼만 길어 가면 모두가 오래 쓸 수 있답니다.",
    "불빛을 낮게 걸어 두면 멀리서도 배가 방향을 잡지. 밤바다는 어둠보다 신호가 무섭소.",
    "배가 흔들릴 때 국물을 가득 담는 건 손님이지. 조금 모자라게 담아야 갑판까지 무사히 갑니다.",
    "돛줄은 젖으면 무거워진다. 도착할 때까지 손에서 놓지 말고.",
}


REPLACEMENTS = {
    "종탑 쪽은 수레가 자주 드나드니, 길 한가운데 서 있지는 마시오.":
        "종탑 쪽은 사람들 발길이 잦소. 길 한가운데 서 있지는 마시오.",
    "그래도 부두에서 일하면 배가 돌아오는 소리를 제일 먼저 듣는다네. 그건 좀 괜찮지.":
        "한 가지 좋은 점은 있지. 부두에선 배가 돌아오는 소리를 제일 먼저 듣는다네.",
    "이 우물은 오래 써도 물맛이 흐려지지 않아요. 필요한 만큼만 길어 가면 모두가 오래 쓸 수 있답니다.":
        "이 우물은 오래 써도 물맛이 변하지 않아요. 필요한 만큼만 길어 가면 모두가 오래 쓸 수 있답니다.",
    "불빛을 낮게 걸어 두면 멀리서도 배가 방향을 잡지. 밤바다는 어둠보다 신호가 무섭소.":
        "불빛을 낮게 걸어 두면 멀리서도 배가 방향을 잡지. 밤바다에선 어둠보다 신호 하나가 더 중요하오.",
    "배가 흔들릴 때 국물을 가득 담는 건 손님이지. 조금 모자라게 담아야 갑판까지 무사히 갑니다.":
        "배가 흔들릴 때 국물을 가득 담아 달라는 건 손님이지. 조금 모자라게 담아야 갑판까지 무사히 갑니다.",
    "돛줄은 젖으면 무거워진다. 도착할 때까지 손에서 놓지 말고.":
        "돛줄은 젖으면 무거워진다. 도착할 때까지 손에서 놓지 마라.",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir",
        default="/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    path = Path(args.dir) / "dialogue.json"
    data = json.loads(path.read_text())
    changed = []

    for npc, node in EPILOGUES.items():
        if npc not in data:
            raise KeyError(f"NPC dialogue set missing: {npc}")
        if "후일담" not in data[npc]:
            data[npc]["후일담"] = node
            changed.append(f"added {npc}/후일담")

    for nodes in data.values():
        for node in nodes.values():
            original_lines = node.get("lines", [])
            lines = [line for line in original_lines if line not in REMOVE_LINES]
            node["lines"] = lines
            if len(lines) != len(original_lines):
                changed.append("removed obsolete ambient copy line")
            for index, line in enumerate(lines):
                replacement = REPLACEMENTS.get(line)
                if replacement and replacement != line:
                    lines[index] = replacement
                    changed.append(f"copy: {line} -> {replacement}")

    for npc, nodes in ADDITIONS.items():
        if npc not in data:
            raise KeyError(f"NPC dialogue set missing: {npc}")
        for key, additions in nodes.items():
            if key not in data[npc]:
                raise KeyError(f"Dialogue node missing: {npc}/{key}")
            lines = data[npc][key].setdefault("lines", [])
            for line in additions:
                if line not in lines:
                    lines.append(line)
                    changed.append(f"{npc}/{key}: {line}")

    if not args.dry_run and changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"changed_lines={len(changed)}")
    for item in changed:
        print(item)


if __name__ == "__main__":
    main()
