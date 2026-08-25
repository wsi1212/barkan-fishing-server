#!/usr/bin/env python3
"""Audit and repair generated quest dialogue without touching authored prose.

The quest writer has a small set of reusable sentence slots.  Older data can
contain a polite sentence in a rough NPC's node (or the reverse), so checking
only the first meeting line is not enough.  This pass recognizes the exact
template sentences and a few objective-bearing template shapes, then renders
them using the NPC voice map from ``rewrite_quest_dialogue.py``.

It deliberately skips elder voices, Hagen's hand-written guild-leader voice,
and NPCs not yet assigned a voice.  Those are reported rather than guessed.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rewrite_quest_dialogue as writer  # noqa: E402


STYLE_INDEX = {"formal_o": 0, "polite": 1, "rough": 2, "authority": 3}
SKIP_STYLES = {"elder", "guild_leader", "friendly"}
Q_PREFIXES = ("인사/", "진행중/", "퀘스트완료/")
Q_SPECIAL = {"첫만남", "후일담"}


AUTHORED_COPY_EDITS = {
    "마리": {
        "조합에 쓸 재료가 늘 부족해요.": "조합에 쓸 재료가 늘 부족해.",
        "비늘은 물고기에서 얻고, 부품도 직접 만들어야 하거든요. 필요한 일을 골라 도와주실래요?":
            "비늘은 물고기에서 얻고, 부품도 직접 만들어야 해. 필요한 일 골라 도와줄래?",
    },
    "카림": {
        "모래 위의 대장간을 지키오.": "모래 위의 대장간을 지켜.",
        "모루가 뜨겁소. 구경은 문 밖에서 하시오.": "모루가 뜨거워. 구경은 문 밖에서 해.",
        "장비에 쓸 재료를 구해다 주겠소?": "장비에 쓸 재료 구해다 줄래?",
        "…제단에 올릴 게 필요하오.": "…제단에 올릴 게 필요해.",
        "어종별 실제 기준 크기 이상이고 A등급인 물고기 다섯 마리요. 상한 건 안 받소.":
            "어종별 실제 기준 크기 이상이고 A등급인 물고기 다섯 마리. 상한 건 안 받아.",
        "제단 가운데가 패어 있는 건… 신경 쓰지 마시오. 원래 그랬소.":
            "제단 가운데가 패어 있는 건… 신경 쓰지 마. 원래 그랬어.",
        "…아직이오.": "…아직이야.",
        "됐소.": "됐어.",
        "…한 가지만. 서쪽 호수엔 가지 마시오.": "…한 가지만. 서쪽 호수엔 가지 마.",
        "물이 식지를 않소. 이유는 나도 모르고, 알고 싶지도 않소.":
            "물이 식질 않아. 이유는 나도 모르고, 알고 싶지도 않아.",
        "사막세이지는 그늘진 바위 틈에서 잘 자란다네.": "사막세이지는 그늘진 바위 틈에서 잘 자라.",
    },
    "유세프": {
        "오아시스 어장을 관리하고 있소.": "오아시스 어장을 관리하고 있어.",
        "일손이 필요하던 참이오.": "일손이 필요하던 참이야.",
        "사막이 사람을 고르는 방식이 있소.": "사막이 사람을 고르는 방식이 있어.",
        "모래는 재촉하지 않소.": "모래는 재촉하지 않아.",
        "…내가 낸 시험이 아니오. 나도 전해 들었을 뿐이지.": "…내가 낸 시험은 아니야. 나도 전해 들었을 뿐이지.",
        "됐소. 이 땅이 자네를 알아본 거요.": "됐어. 이 땅이 자네를 알아본 거야.",
        "…나도 이걸 통과한 사람은 처음 보오.": "…나도 이걸 통과한 사람은 처음 봐.",
    },
    "도란": {
        "상단 바르칸 지부의 도란이라 하오.": "상단 바르칸 지부의 도란이에요.",
        "이름을 알았다고 끝난 게 아니오. 돈이 어디로 갔는지가 남았소.":
            "이름을 알았다고 끝난 게 아니에요. 돈이 어디로 갔는지가 남았어요.",
        "장부 뒷장은 장사를 해 본 사람 눈에만 보이오.": "장부 뒷장은 장사를 해 본 사람 눈에만 보여요.",
        "예순 번 팔고, 사십만 원을 손에 쥐고 오시오.": "예순 번 팔고, 사십만 원을 손에 쥐고 오세요.",
        "뒷장은 도망 안 가오. 앞장부터 채우시오.": "뒷장은 도망 안 가요. 앞장부터 채우세요.",
        "…역시 그렇군. 우리 돈이 우리를 팔았소.": "…역시 그렇군요. 우리 돈이 우리를 팔았어요.",
        "이 장부는 왕도로 가져가야겠소.": "이 장부는 왕도로 가져가야겠어요.",
    },
    "마르코": {
        "사막 상단의 마르코올시다.": "사막 상단의 마르코예요.",
    },
    "길드접수원": {
        "어서 오세요. 방금 부선에서 내리신 분이죠? 소금 냄새가 아직 나는데요.":
            "어서 왔네. 방금 부선에서 내렸지? 소금 냄새가 아직 나는데.",
        "낚시사 길드 접수창구입니다. 저는 요한이라고 합니다.":
            "낚시사 길드 접수창구야. 난 요한이고.",
        "…아, 놀라지 마세요. 이 서류 더미는 오늘 몫이 아니라 이번 달 몫입니다.":
            "…아, 놀라지 마. 이 서류 더미는 오늘 몫이 아니라 이번 달 몫이야.",
        "어부 명부에 이름을 올리러 오셨겠죠. 순서가 있습니다.":
            "어부 명부에 이름 올리러 왔지? 순서가 있어.",
        "먼저 강가의 할아버지께 가서 낚싯대를 쥐어 보십시오.":
            "먼저 강가 할아버지한테 가서 낚싯대를 쥐어 봐.",
        "그분이 「이 사람 물고기 잡을 줄 안다」고 하시면, 제가 명부에 잉크를 씁니다.":
            "그분이 「이 사람 물고기 잡을 줄 안다」고 하시면, 내가 명부에 잉크를 써.",
        "오셨군요. 아직 명부에는 못 올렸습니다 — 절차가 남아서요.":
            "왔군. 아직 명부에는 못 올렸어 — 절차가 남아서.",
        "강가의 할아버지. 화살표가 가리키는 쪽입니다.": "강가의 할아버지. 화살표가 가리키는 쪽이야.",
        "그분께 낚시를 배우고 오시면, 그때 이름을 씁니다.": "그분한테 낚시 배우고 오면, 그때 이름을 써.",
        "할아버지를 아직 못 만나셨군요.": "할아버지를 아직 못 만났군.",
        "길드 회관을 나가서 강가 쪽으로 내려가시면 됩니다. 낚시터 근처에 계십니다.":
            "길드 회관 나가서 강가 쪽으로 내려가면 돼. 낚시터 근처에 있어.",
        "…길을 잃으셨다면 그건 흠이 아닙니다. 이 마을 골목은 저도 3년 걸렸습니다.":
            "…길을 잃었다고 흠은 아니야. 이 마을 골목은 나도 3년 걸렸어.",
        "명부에 잉크가 잘 말랐습니다. 이제 정식으로 이 열도의 어부시군요.":
            "명부 잉크가 잘 말랐군. 이제 정식으로 이 열도의 어부야.",
        "저는 여기서 계속 기록만 합니다. 자네가 뭘 잡아 오는지도 다 이 장부에 남습니다.":
            "난 여기서 계속 기록만 해. 자네가 뭘 잡아 오는지도 다 이 장부에 남아.",
        "…언젠가 아주 큰 걸 잡아 오세요. 그러면 제가 새 장을 펴야 하니까.":
            "…언젠가 아주 큰 걸 잡아 와. 그러면 내가 새 장을 펴야 하니까.",
    },
}


def load_fixed_templates() -> dict[str, tuple[str, ...]]:
    """Read the original fixed-template table without executing its script."""
    tree = ast.parse((HERE / "fix_dialogue_tone.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "T" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            return {key: tuple(values) for key, values in value.items()}
    raise RuntimeError("fix_dialogue_tone.py의 고정 템플릿 표를 찾지 못했습니다")


FIXED_TEMPLATES = load_fixed_templates()


def is_quest_node(key: str) -> bool:
    return key.startswith(Q_PREFIXES) or key in Q_SPECIAL


def exact_template(line: str, voice: str) -> str | None:
    """Return the voice-specific rendering for a known fixed template."""
    index = STYLE_INDEX.get(voice)
    if index is None:
        return None
    for source, variants in FIXED_TEMPLATES.items():
        if line == source or line in variants:
            return variants[index]
    return None


def extra_template(line: str, voice: str) -> str | None:
    """Handle small templates introduced after the original 46-slot set."""
    index = STYLE_INDEX.get(voice)
    if index is None:
        return None
    extra = {
        "좋아요. 필요한 건 모두 모였어요.": (
            "좋소. 필요한 건 모두 모였소.", "좋아요. 필요한 건 모두 모였어요.",
            "좋아. 필요한 건 다 모였어.", "좋다. 필요한 것은 모두 모였다.",
        ),
        "좋아요. 필요한 건 모두 갖춰졌어요.": (
            "좋소. 필요한 것은 모두 갖춰졌소.", "좋아요. 필요한 건 모두 갖춰졌어요.",
            "좋아. 필요한 건 다 갖춰졌어.", "좋다. 필요한 것은 모두 갖춰졌다.",
        ),
        "좋소. 필요한 건 모두 모였소.": (
            "좋소. 필요한 건 모두 모였소.", "좋아요. 필요한 건 모두 모였어요.",
            "좋아. 필요한 건 다 모였어.", "좋다. 필요한 것은 모두 모였다.",
        ),
        "좋소. 필요한 것은 모두 갖춰졌소.": (
            "좋소. 필요한 것은 모두 갖춰졌소.", "좋아요. 필요한 건 모두 갖춰졌어요.",
            "좋아. 필요한 건 다 갖춰졌어.", "좋다. 필요한 것은 모두 갖춰졌다.",
        ),
        "천천히 해도 좋네.": (
            "천천히 하시오.", "천천히 하세요.", "천천히 해.", "천천히 진행하라.",
        ),
        "서두를 필요는 없네.": (
            "서두를 필요는 없소.", "서두를 필요는 없어요.", "서두를 필요는 없어.", "서두를 필요는 없다.",
        ),
        "마치면 다시 이야기해요.": (
            "마치면 다시 이야기합시다.", "마치면 다시 이야기해요.", "마치면 다시 얘기하자.", "마치면 보고하라.",
        ),
        "맡은 일을 마치고 돌아오게.": (
            "맡은 일을 마치고 돌아오시오.", "맡은 일을 마치고 돌아오세요.", "맡은 일 마치고 돌아와.", "맡은 일을 마치고 돌아오라.",
        ),
        "마치시면 제게 알려 주세요.": (
            "마치면 내게 알려 주시오.", "마치시면 제게 알려 주세요.", "끝나면 알려 줘.", "완료하면 보고하라.",
        ),
        "약속한 보상을 챙겨 가세요.": (
            "약속한 보상을 챙겨 가시오.", "약속한 보상을 챙겨 가세요.", "약속한 보상 챙겨.", "약속한 보상을 챙기라.",
        ),
        "약속한 보상을 받아 가세요.": (
            "약속한 보상을 받아 가시오.", "약속한 보상을 받아 가세요.", "약속한 보상 받아.", "약속한 보상을 수령하라.",
        ),
        "준비되시면 천천히 살펴보고 시작해 주세요.": (
            "준비되면 천천히 살펴보고 시작하시오.", "준비되시면 천천히 살펴보고 시작해 주세요.", "준비되면 천천히 보고 시작해.", "준비되는 대로 시작하라.",
        ),
        "내용을 확인하고 준비되면 시작해 주세요.": (
            "내용을 확인하고 준비되면 시작하시오.", "내용을 확인하고 준비되면 시작해 주세요.", "내용 확인하고 준비되면 시작해.", "내용을 확인하고 시작하라.",
        ),
        "조건을 확인하시고 준비가 되면 시작해 주세요.": (
            "조건을 확인하고 준비되면 시작하시오.", "조건을 확인하시고 준비가 되면 시작해 주세요.", "조건 확인하고 준비되면 시작해.", "조건을 확인하고 착수하라.",
        ),
        "맡긴 일은 모두 마무리됐어요.": (
            "맡긴 일은 모두 마무리됐소.", "맡긴 일은 모두 마무리됐어요.", "맡긴 일은 다 끝났어.", "맡긴 일은 모두 마무리됐다.",
        ),
        "이제는 제가 아니라, 다음 사람에게 손을 내밀 차례일지도 모르겠네요.": (
            "이제는 제가 아니라, 다음 사람에게 손을 내밀 차례일지도 모르겠소.",
            "이제는 제가 아니라, 다음 사람에게 손을 내밀 차례일지도 모르겠네요.",
            "이제는 내가 아니라 네가 다음 사람한테 손 내밀 차례일지도 몰라.",
            "이제는 내가 아니라 그대가 다음 사람에게 손을 내밀 차례일지도 모른다.",
        ),
    }
    values = extra.get(line)
    return values[index] if values else None


def dynamic_template(line: str, voice: str) -> str | None:
    """Repair objective lines whose middle contains quest-specific text."""
    if voice in SKIP_STYLES:
        return None

    # Accept/first-meeting objective forms.
    patterns = [
        (r"^이번에 맡길 일은 (.+?)(이라네|이네|이에요|이오|이야|이다)\.$", "맡길"),
        (r"^해야 할 일은 (.+?)(이라네|이네|이에요|이오|이야|이다)\.$", "해야"),
        (r"^처음 부탁(?:드릴|할) 일은 (.+?)(이라네|이네|이에요|이오|이야|이다)\.$", "처음"),
        (r"^이번 부탁은 (.+?)(예요|이에요|이오|이야|이다|야)\.$", "이번"),
        (r"^부탁 하나만 할게요\. (.+?)(예요|이에요|이오|이야|이다)\.$", "하나"),
        (r"^부탁 하나 하겠소\. (.+?)(예요|이에요|이오|이야|이다)\.$", "하나"),
        (r"^할 일은 간단해\. (.+?)(예요|이에요|이오|이야|이다|야)\.$", "간단"),
    ]
    for pattern, kind in patterns:
        match = re.fullmatch(pattern, line)
        if not match:
            continue
        goal = match.group(1)
        if kind == "맡길":
            endings = {
                "formal_o": f"이번에 맡길 일은 {goal}이오.",
                "polite": f"이번에 맡길 일은 {goal}이에요.",
                "rough": f"이번에 맡길 일은 {goal}이야.",
                "authority": f"이번에 맡길 일은 {goal}이다.",
            }
        elif kind == "해야":
            endings = {
                "formal_o": f"해야 할 일은 {goal}이오.",
                "polite": f"해야 할 일은 {goal}이에요.",
                "rough": f"해야 할 일은 {goal}이야.",
                "authority": f"해야 할 일은 {goal}이다.",
            }
        elif kind == "처음":
            prefix = "처음 부탁드릴 일은" if "부탁드릴" in line else "처음 부탁할 일은"
            endings = {
                "formal_o": f"{prefix} {goal}이오.",
                "polite": f"{prefix} {goal}이에요.",
                "rough": f"{prefix} {goal}이야.",
                "authority": f"{prefix} {goal}이다.",
            }
        elif kind == "이번":
            endings = {
                "formal_o": f"이번 부탁은 {goal}이오.",
                "polite": f"이번 부탁은 {goal}예요.",
                "rough": f"이번 부탁은 {goal}야.",
                "authority": f"이번 임무는 {goal}이다.",
            }
        elif kind == "간단":
            endings = {
                "formal_o": f"할 일은 간단하오. {goal}이오.",
                "polite": f"할 일은 간단해요. {goal}이에요.",
                "rough": f"할 일은 간단해. {goal}이야.",
                "authority": f"임무는 간단하다. {goal}이다.",
            }
        else:
            endings = {
                "formal_o": f"부탁 하나 하겠소. {goal}이오.",
                "polite": f"부탁 하나만 할게요. {goal}이에요.",
                "rough": f"부탁 하나 할게. {goal}이야.",
                "authority": f"그대에게 {goal}을 맡기겠다.",
            }
        return endings[voice]

    match = re.fullmatch(r"^이번에는 (.+?) (부탁드릴게요|부탁하오)\.$", line)
    if match:
        goal = match.group(1)
        return {
            "formal_o": f"이번에는 {goal} 부탁하오.",
            "polite": f"이번에는 {goal} 부탁드릴게요.",
            "rough": f"이번엔 {goal} 부탁할게.",
            "authority": f"이번에는 {goal}을 맡기겠다.",
        }[voice]

    match = re.fullmatch(r"^먼저 (.+?)부터 (해 보시면 돼요|해보면 되오|해보면 되네|해보면 돼|해 봐)\.$", line)
    if match:
        goal = match.group(1)
        return {
            "formal_o": f"먼저 {goal}부터 해 보시오.",
            "polite": f"먼저 {goal}부터 해 보세요.",
            "rough": f"먼저 {goal}부터 해 봐.",
            "authority": f"먼저 {goal}부터 하라.",
        }[voice]

    # Progress objective forms.
    match = re.fullmatch(r"^아직 (.+?) (남아 있어요|남아 있소|남았군|남았어|남아 있네|남았네)\.$", line)
    if match:
        goal = match.group(1)
        return {
            "formal_o": f"아직 {goal} 남아 있소.",
            "polite": f"아직 {goal} 남아 있어요.",
            "rough": f"아직 {goal} 남았어.",
            "authority": f"아직 {goal} 남았다.",
        }[voice]

    match = re.fullmatch(r"^아직 (.+?)(을|를) (끝내지 못했군|못 끝냈군|끝내지 못했소|끝내지 못했다|못 끝냈어요|끝내지 못했어요)\.$", line)
    if match:
        goal, particle = match.group(1), match.group(2)
        return {
            "formal_o": f"아직 {goal}{particle} 끝내지 못했소.",
            "polite": f"아직 {goal}{particle} 끝내지 못했어요.",
            "rough": f"아직 {goal}{particle} 못 끝냈어.",
            "authority": f"아직 {goal}{particle} 끝내지 못했다.",
        }[voice]

    # Completion objective forms.
    match = re.fullmatch(r"^(.+?)(을|를) 마치셨네요\. 큰 도움이 됐어요\.$", line)
    if match:
        goal, particle = match.group(1), match.group(2)
        return {
            "formal_o": f"{goal}{particle} 마쳤소. 큰 도움이 됐소.",
            "polite": line,
            "rough": f"{goal}{particle} 끝냈어. 수고했어.",
            "authority": f"{goal}{particle} 완수했다. 기록해 두겠다.",
        }[voice]
    match = re.fullmatch(r"^(.+?)(을|를) 마쳤네요\. 고마워요\.$", line)
    if match:
        goal, particle = match.group(1), match.group(2)
        return {
            "formal_o": f"{goal}{particle} 마쳤소. 고맙소.",
            "polite": line,
            "rough": f"{goal}{particle} 끝냈어. 고마워.",
            "authority": f"{goal}{particle} 완수했다. 수고했다.",
        }[voice]
    return None


def normalize_line(line: str, voice: str) -> str:
    if voice in SKIP_STYLES:
        return line
    for converter in (exact_template, extra_template, dynamic_template):
        replacement = converter(line, voice)
        if replacement is not None:
            return replacement
    return line


def authored_copy_edit(npc: str, line: str) -> str:
    return AUTHORED_COPY_EDITS.get(npc, {}).get(line, line)


def run(base: Path, dry_run: bool, no_backup: bool) -> dict:
    path = base / "dialogue.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    nodes = 0
    mapped = set()
    unmapped = set()
    samples = []
    for npc, npc_nodes in data.items():
        voice = writer.style(npc)
        has_quest = any(is_quest_node(key) for key in npc_nodes)
        if has_quest:
            if voice in SKIP_STYLES:
                unmapped.add(npc) if voice == "friendly" else None
            else:
                mapped.add(npc)
        for key, node in npc_nodes.items():
            if not is_quest_node(key):
                continue
            lines = node.get("lines") or []
            before = list(lines)
            node["lines"] = [authored_copy_edit(npc, normalize_line(line, voice)) for line in lines]
            count = sum(a != b for a, b in zip(before, node["lines"]))
            if count:
                changed += count
                nodes += 1
                if len(samples) < 12:
                    samples.append(f"{npc}/{key}: {before} -> {node['lines']}")
    if not dry_run:
        if not no_backup:
            backup = path.with_suffix(".json.bak-tone-all")
            if not backup.exists():
                shutil.copy2(path, backup)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "dir": str(base),
        "changed_lines": changed,
        "changed_nodes": nodes,
        "mapped_quest_npcs": sorted(mapped),
        "unmapped_quest_npcs": sorted(unmapped),
        "dry_run": dry_run,
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(Path(args.dir), args.dry_run, args.no_backup), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
