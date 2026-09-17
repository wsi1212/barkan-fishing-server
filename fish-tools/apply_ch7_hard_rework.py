#!/usr/bin/env python3
"""Apply the approved Chapter 7 hard-rework to every required data mirror.

The content mirror, dev runtime copy, and plugin-source copy are deliberately
updated together: deploy-blockship's copy-drift gate rejects a partial edit.
This changes existing quest objectives/rewards only; IDs, quest chain, NPC
assignment, and special rewards remain intact.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHS = (
    ROOT / "ops/blockship-data/quests.json",
    Path("/Users/user/Library/Application Support/feather/player-server/servers/"
         "07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BlockShip/quests.json"),
    Path.home() / "development/blockship-plugin/quests.json",
)

GOALS = {
    "심해01": ["harpoon|아무|S|6|0"],
    "심해02": ["sell|150"],
    "심해03": ["fish|아무|S|7|0", "submitmat|녹슨부품|100"],
    "심해04": ["harpoon|아무|S|10|0"],
    "심해04b": ["craft|쾌속선_작살|1", "submitmat|철광석|50"],
    "심해05": ["submitmat|산호조각|100"],
    "심해05b": ["submitmat|압축철광석|180"],
    "심해06": ["dogam|대양|28", "fish|아무|S|6|0"],
    "심해07": ["sail|7500"],
    "심해08": ["fish|아무|S|12|0"],
    "심해09": ["fish|교단의해도|아무|2|0", "submitmat|안개수정|50"],
    "심해10": ["usebait|50", "iceboxstore|12"],
    "심해10b": ["cook|바르칸 채집 성찬|1", "submitdish|채집성찬|1"],
    "심해11": ["fish|향유고래|아무|1|0", "submitmat|용비늘|50"],
    "심해12": ["sail|15000"],
    "심해12b": ["craft|바르칸_찌|1", "usebait|40"],
    "심해13": ["sail|20000", "harpoon|아무|S|15|0", "harpoon|아무|M|1|0"],
    "심해14": ["fish|교단의해도|아무|3|0", "dogam|대양|32"],
    "알비스00": ["fish|교단의표식|아무|5|0", "submitmat|진주|100"],
    "알비스01": ["fish|아무|S|8|0"],
    "알비스02": ["fish|성광어|아무|1|0", "iceboxstore|5"],
    "심해15": ["fish|교단의표식|아무|8|0", "submitmat|거대비늘|100"],
    "심해16": ["dogam|기억의_연못|5", "fish|아무|S|6|0"],
    "심해17": ["dogam|기억의_연못|5", "submitmat|진주|100"],
    "심해18": ["submitmat|별빛진주|100"],
    "심해18b": ["dogam|오아시스|38", "submitmat|보석|50"],
    "심해19": ["fish|아무|S|8|0", "fish|성광어|아무|1|0"],
    "심해20": ["sail|25000", "submitmat|심해수정|50"],
    "심해21": ["skill|20", "enhance|20"],
    "심해22": ["craft|심해_잠수_작살|1", "submitmat|심해수정|100"],
    "심해23": ["enhance|25", "submitmat|압축흑정석|180"],
    "심해24": ["forage|barkan:forage_z_glowshroom|12"],
    "심해25": ["level|67", "dogam|대양|35", "fish|아무|M|3|0"],
    "심해26": ["craft|심해어가면|1", "harpoon|아무|S|18|0"],
    "심해27": ["submitmat|고대비늘|100", "harpoon|아무|S|20|0"],
    "심해28": ["submitmat|별빛진주|100"],
    "심해28b": ["mine|자수정|180", "submitmat|자수정|100"],
    "심해29": ["harpoon|아무|S|25|0"],
    "심해30": ["dogam|대양|40", "submitmat|바르칸조각|50"],
    "심해30b": ["craft|심연의_작살|1", "enhance|30"],
    "심해31": ["harpoon|아무|M|3|0"],
    "심해32": ["harpoon|아무|M|5|0", "usebait|80"],
    "심해33": ["material|심해전왕의핵|1"],
    "심해34": ["dogam|대양|42", "fish|아무|M|5|0"],
    "심해35": ["fish|아무|M|7|0", "submitmat|용비늘|50"],
}

XP = {
    "심해01": 4000, "심해02": 4500, "심해03": 24500,
    "심해04": 5500, "심해04b": 15000, "심해05": 24500,
    "심해05b": 35500, "심해06": 5000, "심해07": 6500,
    "심해08": 7500, "심해09": 17000, "심해10": 7000,
    "심해10b": 9500, "심해11": 20500, "심해12": 7000,
    "심해12b": 6000, "심해13": 9500, "심해14": 6000,
    "알비스00": 27500, "알비스01": 9000, "알비스02": 7500,
    "심해15": 27000, "심해16": 5500, "심해17": 27000,
    "심해18": 43000, "심해18b": 18500, "심해19": 8000,
    "심해20": 18000, "심해21": 9000, "심해22": 27000,
    "심해23": 38000, "심해24": 7000, "심해25": 8000,
    "심해26": 8000, "심해27": 29000, "심해28": 44000,
    "심해28b": 17000, "심해29": 9000, "심해30": 21000,
    "심해30b": 9000, "심해31": 10500, "심해32": 13000,
    "심해33": 16000, "심해34": 10500, "심해35": 22655,
}

MONEY = {
    "심해03": 412665, "심해04b": 245000, "심해05": 419212,
    "심해05b": 522000, "심해09": 338853, "심해11": 345400,
    "알비스00": 458494, "심해15": 471588, "심해17": 471588,
    "심해18": 778135, "심해18b": 378135, "심해20": 384682,
    "심해22": 497776, "심해23": 597776, "심해27": 517417,
    "심해28": 823964, "심해28b": 360000, "심해30": 423964,
    "심해35": 437058,
}

assert len(GOALS) == len(XP) == 45


def update(path: Path) -> None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    quests = raw["퀘스트"]
    missing = sorted(set(GOALS) - set(quests))
    if missing:
        raise RuntimeError(f"{path}: 없는 퀘스트 ID {missing}")
    for qid, goals in GOALS.items():
        quests[qid]["목표"] = goals
        quests[qid]["보상경험치"] = XP[qid]
        if qid in MONEY:
            quests[qid]["보상돈"] = MONEY[qid]
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


for path in PATHS:
    update(path)
    print(f"✓ {path}")
