#!/usr/bin/env python3
"""Prepare the ImageGen queue from authoritative NPC, dialogue, quest and skin data."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BLOCKSHIP = Path("/Users/user/development/blockship-plugin")
NPC_PATH = BLOCKSHIP / "npc.json"
DIALOGUE_PATH = BLOCKSHIP / "dialogue.json"
QUEST_PATH = BLOCKSHIP / "quests.json"
MANIFEST_PATH = ROOT / "npc-profiles" / "manifest.json"
OUT = ROOT / "npc-profiles" / "imagegen-batch" / "queue.json"

IDENTITY = ROOT / "npc-profiles" / "imagegen-batch" / "identity"
STYLE = ROOT / "npc-profiles" / "references" / "otto-imagegen-style-reference.png"
BETTERHUD = ROOT / "ops" / "prod" / "betterhud" / "assets" / "dialogue" / "portrait-grandfather-hud.png"

STATE_KO = {
    "base": "기본·인사: 캐릭터의 자연스러운 친근한 표정",
    "talk": "대화·설명: 말하고 가르치거나 안내하는 표정과 열린 손짓",
    "happy": "기쁨·완료: 따뜻한 미소와 성취를 축하하는 표정",
    "worried": "걱정·경고: 상황을 염려하는 눈썹과 진지한 표정",
    "stern": "엄격·주의: 권위 있고 단호하지만 과장되지 않은 표정",
    "surprised": "놀람·반응: 눈썹을 올린 생생한 반응",
}


def flatten_dialogue(node: object) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        for value in node.values():
            if isinstance(value, dict):
                out.extend(str(x) for x in (value.get("lines") or []))
    return out


def state_set(lines: list[str], roles: list[str], name: str, quests: list[str]) -> list[str]:
    text = " ".join(lines)
    states = ["base"]
    if lines:
        states.append("talk")
    # Keep the generated sheet compact: the emotional states are selected from
    # the actual dialogue vocabulary, not from the NPC role alone.
    if re.search(r"기쁘|좋아|환영|축하|고맙|하하|웃|멋지|다행|반갑|해냈|완료|합격|성공", text):
        states.append("happy")
    if re.search(r"위험|조심|비밀|두렵|걱정|슬프|잃|죄송|미안|죽|안개|그림자|심연", text):
        states.append("worried")
    if re.search(r"!|당장|어서|감히|싫|화|분노|안 돼|금지|시험|명령|서두르", text):
        states.append("stern")
    if re.search(r"어\?|정말|뭐지|놀랍|처음|설마|오!|허!|…", text):
        states.append("surprised")
    # Functional-only NPCs have no dialogue state to justify an expression.
    if not lines and roles:
        return ["base"]
    # Four panels are the default sheet budget. Quest/story NPCs with a clear
    # completion cue retain happy; otherwise keep the most dialogue-relevant
    # reaction after talk.
    return list(dict.fromkeys(states))[:4]


def snippets(lines: list[str]) -> list[str]:
    clean = []
    for line in lines:
        line = re.sub(r"&[0-9a-fk-or]", "", line, flags=re.I).strip()
        if line and line not in clean:
            clean.append(line)
    return clean[:10]


def main() -> None:
    npcs = json.loads(NPC_PATH.read_text(encoding="utf-8"))["npcs"]
    dialogues = json.loads(DIALOGUE_PATH.read_text(encoding="utf-8"))
    quest_data = json.loads(QUEST_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["npcs"]
    by_name = {x["npc"]: x for x in manifest}
    # Quest data is included as textual grounding where the NPC's npc.json list
    # is incomplete or only names a quest family.
    quest_text = json.dumps(quest_data, ensure_ascii=False)
    queue = []
    for name, data in npcs.items():
        if name == "할아버지":
            continue  # The approved six-image pilot is already complete.
        meta = by_name[name]
        lines = flatten_dialogue(dialogues.get(name, {}))
        roles = [k for k, v in data.items() if v is True]
        states = state_set(lines, roles, name, data.get("quests", []))
        skin = ROOT / "skin-forge" / "out" / f"{meta['skin']}.png"
        identity = IDENTITY / f"{meta['skin']}.png"
        if len(states) == 1:
            layout = "single"
        else:
            layout = "grid2x2"
        quest_names = list(data.get("quests") or [])
        role_text = ", ".join(roles) if roles else "스토리/대화형"
        grounding = " / ".join(snippets(lines))
        prompt = f"""Use case: illustration-story. Asset type: Minecraft server BetterHUD dialogue portrait.
Create a polished premium pixel-art portrait asset for the exact NPC '{name}' ({data.get('name', name)}), Citizens ID {data['citizensId']}.

Authoritative identity: the attached identity board and 64x64 Minecraft skin are the exact current skin for this NPC. Preserve its face, hair, skin tone, headwear, colors, garments, trim, asymmetry, and recognizable silhouette. Treat the identity board and skin as clothing truth; do not replace them with generic fantasy clothing and do not add props that are not supported by the skin or role. Input image 1 is the large identity board for this exact NPC. Input image 2 is the exact 64x64 skin texture. Input image 3 is a BetterHUD portrait style reference only; do not copy the person, clothing, cap, beard, or palette from that reference.

Role and story grounding: {role_text}. Related quests: {', '.join(quest_names) if quest_names else '없음'}.
Dialogue evidence: {grounding if grounding else '대화문 없음; 역할과 스킨의 직업성이 표정과 자세의 근거다.'}

Output layout: {layout}. Create exactly {len(states)} separate portrait panel(s), one per state in this order: {', '.join(states)}. For grid2x2, use a clean equal 2-by-2 grid with no labels, no borders, no text, and no panel overlap. Each panel must contain the same NPC in a consistent three-quarter waist-up dialogue framing, same head size, same top alignment, no feet, and similar visible footprint as the approved reference. For single, create one portrait with that same framing.

State direction: {'; '.join(STATE_KO[s] for s in states)}.
If a state is completion-related, show the character reacting to the player's success. If a state is worried or stern, keep it readable and characterful rather than angry by default. Make poses differ subtly (open hand, holding/using role item, attentive stance) while preserving the exact identity and clothing.

Backdrop: perfectly flat solid #00ff00 chroma-key background only. No gradient, texture, floor, shadow, reflection, watermark, UI, speech bubble, extra characters, or labels. Do not use #00ff00 in the character."""
        queue.append({
            "citizensId": int(data["citizensId"]),
            "npc": name,
            "displayName": data.get("name", name),
            "skin": meta["skin"],
            "skin_path": str(skin),
            "roles": roles,
            "quests": quest_names,
            "dialogue_lines": lines,
            "states": states,
            "layout": layout,
            "references": [str(identity), str(skin), str(BETTERHUD)],
            "prompt": prompt,
        })
    OUT.write_text(json.dumps({"style": str(STYLE), "identity_dir": str(IDENTITY), "queue": queue}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    from collections import Counter
    print(json.dumps({"queued": len(queue), "panels": sum(len(x["states"]) for x in queue), "layouts": Counter(x["layout"] for x in queue), "states": Counter(s for x in queue for s in x["states"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
