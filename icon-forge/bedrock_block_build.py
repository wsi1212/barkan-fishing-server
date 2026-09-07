#!/usr/bin/env python3
"""베드락(Geyser) 커스텀 «블록» 생성기 — 디스플레이 엔티티로 그리던 3D 모델을 베드락에서도 보이게.

왜 필요한가
    Geyser 에는 ItemDisplay/BlockDisplay 번역기가 없다(jar 실측 2.11.2: DisplayBaseEntity·
    TextDisplayEntity·InteractionEntity 뿐). 그래서 채집 노드·특수작물처럼 «디스플레이로 그리는»
    것은 베드락에서 전부 투명하다. 커스텀 «블록» 은 Geyser 가 지원하므로, 베드락 뷰어에게만
    그 블록을 보내면(BedrockBlockMirror) 진짜 3D 모델이 보인다.

실기기로 확정한 규칙 (2026-09-06, A/B 반복)
    · collision_box·selection_box 를 «건드리면» 베드락이 블록을 아예 그리지 않는다.
      false 도, 크기 0 도 마찬가지. 그냥 두는 것이 정답이다.
    · state_overrides 는 최상위 정의를 «상속» 한다 — 최상위에 넣은 필드가 하위 상태까지 간다.
      (그래서 위 박스 하나가 66종 전부의 렌더를 죽였다.)
    · destructible_by_mining 을 크게 주면 탭해도 안 부서지고 렌더는 그대로다. 이게 없으면
      베드락에서 탭할 때마다 블록이 사라졌다 돌아온다.
    · 채집/수확 클릭은 «우클릭만» 받는다(유저 결정). 좌클릭까지 받으면 탭 한 번이 파괴 예측과
      입력을 동시에 일으켜 깜빡인다.

베이스 자바 블록
    minecraft:tripwire — 상태 128개(7 boolean). 우리 월드에 실물이 있을 일이 없어야 한다.
    ★실물이 있으면 그 자리가 베드락 유저에게 채집물로 보인다. 블록을 바꿀 땐 이 조건부터 볼 것.

산출물
    out/bedrock/barkan_blocks.json   → Geyser custom_mappings/
    out/bedrock/bedrock-blocks.json  → plugins/BlockShip/ (자바가 읽어 그 blockstate 를 보낸다)
    out/bedrock/barkan_bedrock.mcpack 에 geometry·텍스처 병합(아이템 팩과 «같은 팩» 이다)
"""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import yaml
from PIL import Image

from bedrock_geo import java_to_geo

HERE = Path(__file__).resolve().parent
SERVER = Path("/Users/user/Library/Application Support/feather/player-server/"
              "servers/07de2d81-991a-47e2-b62d-06c0d1b5150a")
CE = SERVER / "plugins/CraftEngine/resources/barkan_furniture"
ASSETS = CE / "resourcepack/assets"
OUT = HERE / "out/bedrock"
STAGE = OUT / "pack"

# ★한 베이스 블록에 «65개째부터는 안 먹는다» (2026-09-07 실측).
#   66종을 tripwire 하나에 몰아넣었더니 정렬 순서로 64·65번(황금이삭·물냉이)만
#   state_overrides 가 무시되고 «최상위 기본 지오메트리»(=0번 양배추)로 그려졌다.
#   유저 제보: 「황금이삭이 특수양배추 자라는 도중처럼 보임」 — 정확히 그 폴백이다.
#   Geyser/베드락 어느 쪽 상한인지는 못 밝혔지만 경계는 64로 깨끗하다.
#   ⇒ 베이스를 여러 개 두고 «베이스당 64개» 로 끊는다.
PER_BASE_CAP = 64

# 베이스 후보 — 전부 boolean 프로퍼티만 가진 블록이어야 상태 문자열을 비트로 만들 수 있다.
#   ★우리 월드에 «실물이 있을 일이 없어야» 한다. 실물이 있으면 그 자리가 베드락 유저에게
#     채집물로 보인다. 블록을 바꿀 땐 이 조건부터 볼 것.
#   · tripwire     — 7 bool. 함정선은 우리가 안 쓴다.
#   · chorus_plant — 6 bool. 엔드에만 자연 생성된다(우리 콘텐츠는 엔드를 안 쓴다).
#     ★glow_lichen·vine·sculk_vein 은 쓰지 말 것 — 동굴·정글·딥다크에 흔하다(광산이 있다).
BASES = [
    ("minecraft:tripwire", ["attached", "disarmed", "east", "north", "powered", "south", "west"]),
    ("minecraft:chorus_plant", ["down", "east", "north", "south", "up", "west"]),
]
BASE_BLOCK = BASES[0][0]     # 하위호환(옛 로그·문서용)
PROPS = BASES[0][1]
DESTRUCT = 1000000          # 사실상 파괴 불가(탭으로 사라지지 않게)

CONFIGS = [("forage", "forage_custom.yml"), ("crop", "crops.yml")]


def gui_or_solid(model):
    """CE 의 model 필드에서 «놓였을 때 보이는» 3D 모델 경로를 뽑는다.

    채집물은 select 구조로 gui(2D 아이콘)와 fallback(3D)이 갈린다 — 블록으로 보여 줄 것은
    바닥에 놓이는 쪽이므로 fallback 이다. 작물은 그냥 문자열이다.
    """
    if isinstance(model, str):
        return model
    if not isinstance(model, dict):
        return None
    if "fallback" in model:
        return gui_or_solid(model["fallback"])
    if "model" in model:
        return gui_or_solid(model["model"])
    for case in model.get("cases") or []:
        got = gui_or_solid(case.get("model"))
        if got:
            return got
    return None


def texture_of(model_id: str):
    if not model_id or ":" not in model_id:
        return None, None
    ns, path = model_id.split(":", 1)
    mj = ASSETS / ns / "models" / f"{path}.json"
    if not mj.is_file():
        return None, None
    model = json.loads(mj.read_text(encoding="utf-8"))
    tex = model.get("textures") or {}
    tid = tex.get("0") or tex.get("layer0") or next(
        (v for k, v in tex.items() if k != "particle"), None)
    if not tid or ":" not in str(tid):
        return model, None
    tns, tpath = str(tid).split(":", 1)
    png = ASSETS / tns / "textures" / f"{tpath}.png"
    return model, (png if png.is_file() else None)


def state_string(index: int, props: list[str]) -> str:
    """베이스 안에서의 인덱스 → 상태 문자열. 정렬된 id 순서라 매번 같은 값이 나온다."""
    bits = [(index >> i) & 1 for i in range(len(props))]
    return ",".join(f"{p}={'true' if b else 'false'}" for p, b in zip(props, bits))


def slot_of(i: int):
    """전체 i 번째 종 → (베이스 블록, 프로퍼티목록, 베이스 안 인덱스).

    ★베이스당 PER_BASE_CAP 로 끊는다. 그 위는 조용히 «다른 모양» 이 되므로 넘치면 멈춘다.
    """
    for base, props in BASES:
        cap = min(PER_BASE_CAP, 1 << len(props))
        if i < cap:
            return base, props, i
        i -= cap
    raise SystemExit(f"베이스 상태가 모자라다 — BASES 에 블록을 더 넣을 것"
                     f" (현재 상한 {sum(min(PER_BASE_CAP, 1 << len(pr)) for _, pr in BASES)}종)")


def main() -> int:
    if not STAGE.is_dir():
        raise SystemExit("팩 스테이지가 없다 — 먼저 bedrock_pack_build.py 를 돌릴 것")

    entries = []
    for kind, fname in CONFIGS:
        f = CE / "configuration" / fname
        if not f.is_file():
            print(f"  ⚠ {fname} 없음 — 건너뜀")
            continue
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        got = 0
        for full_id, spec in (doc.get("items") or {}).items():
            if not isinstance(spec, dict) or ":" not in str(full_id):
                continue
            model_id = gui_or_solid(spec.get("model"))
            model, png = texture_of(model_id)
            if not model or not png or not model.get("elements"):
                continue
            ident = str(full_id).split(":", 1)[1]
            entries.append({"kind": kind, "item": str(full_id), "ident": f"bk_{ident}",
                            "model": model, "png": png})
            got += 1
        print(f"  {fname}: {got}종")

    entries.sort(key=lambda e: e["item"])          # ★배정 안정성 — 순서가 바뀌면 배정도 바뀐다
    if not entries:
        raise SystemExit("대상이 없다")

    (STAGE / "models/blocks").mkdir(parents=True, exist_ok=True)
    (STAGE / "textures/blocks").mkdir(parents=True, exist_ok=True)
    tex_data, assign = {}, {}
    per_base: dict[str, dict] = {}   # 베이스 → {상태문자열: 정의}
    first_of: dict[str, str] = {}    # 베이스 → 그 베이스의 0번 ident(최상위 기본 정의용)

    for i, e in enumerate(entries):
        ident = e["ident"]
        w, h = Image.open(e["png"]).size
        (STAGE / f"models/blocks/{ident}.geo.json").write_text(
            json.dumps(java_to_geo(e["model"], f"geometry.barkan.{ident}", w, h), indent=1))
        shutil.copy(e["png"], STAGE / f"textures/blocks/{ident}.png")
        tex_data[ident] = {"textures": f"textures/blocks/{ident}"}
        defn = {
            "geometry": f"geometry.barkan.{ident}",
            "material_instances": {"*": {"texture": ident, "render_method": "alpha_test",
                                         # ★face_dimming 을 끄면 모든 면이 같은 밝기라 «형체 없는
                                         #   덩어리» 로 보인다. 자바는 면 방향마다 음영이 들어간다.
                                         "face_dimming": True, "ambient_occlusion": False}},
            "destructible_by_mining": DESTRUCT,
        }
        base, props, idx = slot_of(i)
        st = state_string(idx, props)
        per_base.setdefault(base, {})[st] = defn
        first_of.setdefault(base, ident)
        assign[e["item"]] = f"{base}[{st}]"

    (STAGE / "textures/terrain_texture.json").write_text(json.dumps({
        "resource_pack_name": "barkan", "texture_name": "atlas.terrain",
        "padding": 8, "num_mip_levels": 4, "texture_data": tex_data}, indent=1))

    # 베이스마다 하나씩 — 최상위 정의는 «그 베이스의 0번» 이 맡는다.
    #   ★상태가 안 걸리면 여기로 폴백한다. 그래서 64개 초과분이 «0번 모양» 으로 보였다.
    blocks = {"format_version": 1, "blocks": {}}
    for base, overrides in per_base.items():
        first = first_of[base]
        blocks["blocks"][base] = {
            "name": "barkan_display" + ("" if base == BASES[0][0] else "_" + base.split(":")[1]),
            "display_name": "바르칸 표시물",
            "included_in_creative_inventory": False,
            # ★박스(collision/selection)는 넣지 않는다 — 넣으면 베드락이 그리지 않는다.
            "geometry": f"geometry.barkan.{first}",
            "material_instances": {"*": {"texture": first, "render_method": "alpha_test",
                                         "face_dimming": True, "ambient_occlusion": False}},
            "destructible_by_mining": DESTRUCT,
            "state_overrides": overrides,
        }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "barkan_blocks.json").write_text(json.dumps(blocks, ensure_ascii=False, indent=2))
    (OUT / "bedrock-blocks.json").write_text(json.dumps(
        {"bases": [b for b, _ in BASES], "blocks": assign}, ensure_ascii=False, indent=2))

    mf = json.loads((STAGE / "manifest.json").read_text())
    for blk in [mf["header"]] + mf["modules"]:
        blk["version"][2] += 1
    (STAGE / "manifest.json").write_text(json.dumps(mf, ensure_ascii=False, indent=2))

    pack = OUT / "barkan_bedrock.mcpack"
    pack.unlink(missing_ok=True)
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(STAGE.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(STAGE).as_posix())

    cap = sum(min(PER_BASE_CAP, 1 << len(pr)) for _, pr in BASES)
    print(f"▶ 커스텀 블록 {len(entries)}종 / 상한 {cap}종 (베이스 {len(per_base)}개, 베이스당 {PER_BASE_CAP})")
    for b, o in per_base.items():
        print(f"     {b}: {len(o)}종")
    print(f"▶ 팩 {pack.stat().st_size // 1024} KB · manifest {mf['header']['version']}")
    print(f"✅ {OUT/'barkan_blocks.json'}\n✅ {OUT/'bedrock-blocks.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
