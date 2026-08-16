#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사막의 물 문제를 왕명에 실어 준다 — `왕도05` 설명 교체 (2026-08-14).

★문제 — 3챕터에서 제기된 **물 도둑질**(오아시스가 줄고 우물이 마른다)이
  4~7챕터 어디에서도 결말을 얻지 못했다. 결정적으로 `왕도05` 설명의 마지막 줄이

      "사막의 일은 이미 영주의 보고로 전달됐습니다."

  로 되어 있어, 물 문제를 **행정적으로 종결 처리**해 버린다. 서류가 넘어갔다는 말이지
  마을이 물을 되찾았다는 말이 아닌데, 서사는 여기서 사막을 놓아 버린다.

★조치 — 왕명에 **사막의 물길**을 명시적으로 실는다. 그러면
  5챕터의 상단 조사·붕괴가 곧 사막 문제의 해결이 되고, 3챕터와 5챕터가 한 줄로 이어진다.
  회수 장면은 7챕터 `심해18b`(사피르)에서 — 오아시스가 차오른 것을 플레이어가 직접 본다.

사용법 — quests.json이 있는 디렉터리에서 실행:
    python3 fix_desert_thread.py
"""
import json, shutil, sys

QP = "quests.json"
Q = json.load(open(QP, encoding="utf-8"))
QUESTS = Q["퀘스트"]

e = QUESTS.get("왕도05")
if e is None:
    sys.exit("✗ 왕도05 없음 — quests.json 경로를 확인하세요")

before = list(e.get("설명", []))
e["설명"] = [
    "&7국왕이 첫 왕명을 내립니다 — &f상단을 조사하라.&7",
    "&7\"사막의 우물은 아직 마른 채다. 물길을 끊은 자를 찾아라.\"",
    "&8사막의 물 문제는 끝난 것이 아니라 왕명에 실렸습니다.",
]

shutil.copy(QP, QP + ".pre-desertfix")
with open(QP, "w", encoding="utf-8") as f:
    json.dump(Q, f, ensure_ascii=False, indent=2)

print("[왕도05] 왕명에 사막의 물길을 싣는다")
for l in before:
    print("   -", l)
for l in e["설명"]:
    print("   +", l)
print("\n✓ 완료. 반영: /데이터리로드")
print("  └ 회수는 7챕터 심해18b(사피르) — build_ch7_quests.py가 생성한다")
