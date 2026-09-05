#!/usr/bin/env python3
"""월드에 손으로 지은 배 → 배 시스템 blueprint(ships/<이름>.json) 생성.

★왜 월드를 직접 읽나: `/ship create` 는 스캔하면서 **원본 블록을 지운다**(ShipFactory.createFromSelection).
  prod 에 서 있는 건물/배를 프리셋으로 뜨려면 파괴 없이 읽어야 한다. 그래서 anvil region 파일을
  직접 파싱한다 — 풀 blockstate(계단 facing, 원목 axis …)가 그대로 나온다.
  ★dev 월드는 prod 미러(mc-sync prod_to_dev)라 dev 파일을 읽어도 prod 와 같다. 실측으로 대조할 것.

★재실행 가능: 프리셋 스펙이 PRESETS 에 박혀 있어 언제든 다시 뽑으면 같은 파일이 나온다
  (id·created 고정). 생성물을 손으로 고치지 말고 여기 스펙을 고칠 것.

블록 분류는 Java `ShipBlock.autoClassify` 를 그대로 옮긴 것 — 양쪽이 갈리면 돛이 안 움직이거나
충돌 셜커가 엉뚱한 데 붙는다.

사용: python3 scan_ship_world.py <프리셋이름>
출력: plugins/BlockShip/ships/<프리셋이름>.json  → 이어서 `bake_ship.py <프리셋> <영문명>`
"""
import json, os, sys, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anvil_read as anvil

SERVER = os.path.expanduser("~/Library/Application Support/feather/player-server/servers/"
                            "07de2d81-991a-47e2-b62d-06c0d1b5150a")
SHIPS = os.path.join(SERVER, "plugins/BlockShip/ships")

# ── 프리셋 스펙 (권위) ────────────────────────────────────────────────────────
# bbox 는 배 전체를 감싸는 월드 좌표(양끝 포함). origin 은 blueprint 상대좌표의 0점.
#  ★origin 의 y = **수면 바로 위 공기칸**으로 잡는다. ShipCollider.findWaterSurface 가
#    「물이면서 위가 공기인 y」+1 을 돌려주고 그 값이 소환 중심 Y 가 되기 때문 — 즉 origin 을
#    지어 놓은 자리의 수면 위 첫 칸에 맞춰야 소환된 배의 흘수가 실제로 지은 모습과 같아진다.
#    (수면 칸에 맞추면 배가 통째로 한 칸 높이 떠서 갑판이 물 위로 올라온다.)
#    minRelY 가 깊을수록 소환에 필요한 수심이 늘어난다(floatsAt 이 minRelY 바로 아래를 물로 요구).
PRESETS = {
    "돛단배": dict(
        world=os.path.join(SERVER, "world"),
        bbox=(415, 58, 1015, 421, 70, 1027),   # prod 스폰항 앞바다에 손으로 지은 소형 범선
        origin=(418, 61, 1021),                # x=용골 중심, y=수면 위 첫 공기칸, z=선체 중앙
        pilot=(418, 61, 1023),                 # 선미 조종석
        passengers=[(418, 61, 1018)],          # 선수 탑승석
        speed=10, duration=90, cooldown=60, price=10000,
        created=1788700000000,
        uuid="6b1f2d4a-8c33-5e17-9a20-0d1c7f4b3e88",
    ),
}


def auto_classify(data: str):
    """Java ShipBlock.autoClassify 이식. → (noCollision, animGroup, scale)"""
    mat = data.split("[")[0].removeprefix("minecraft:").upper()
    if mat.endswith("_WOOL"):
        return True, "sail", [1.0, 1.0, 0.15]
    if mat.endswith("_CARPET"):
        return True, "sail", None
    if "BANNER" in mat:
        return True, "flag", None
    if "FENCE" in mat or mat == "IRON_BARS" or mat.endswith("GLASS_PANE"):
        return True, None, None
    if mat in ("IRON_CHAIN", "LIGHTNING_ROD", "END_ROD"):
        return True, None, None
    if "LANTERN" in mat or "TORCH" in mat:
        return True, None, None
    return False, None, None


SKIP = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def build(name):
    spec = PRESETS[name]
    x1, y1, z1, x2, y2, z2 = spec["bbox"]
    ox, oy, oz = spec["origin"]
    world = anvil.region_blocks(spec["world"], x1, y1, z1, x2, y2, z2)

    blocks, skipped = [], 0
    for (x, y, z), data in sorted(world.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
        base = data.split("[")[0]
        if base in SKIP or base in ("minecraft:water", "minecraft:bubble_column"):
            skipped += 1
            continue
        # 물속에서 뜬 배라 waterlogged 가 켜져 있으면 소환 후에도 물을 달고 다닌다
        data = data.replace("waterlogged=true", "waterlogged=false")
        nc, ag, sc = auto_classify(data)
        b = {"x": x - ox, "y": y - oy, "z": z - oz, "data": data}
        if nc: b["noCollision"] = True
        if ag: b["animGroup"] = ag
        if sc: b["scale"] = sc
        blocks.append(b)

    if not blocks:
        raise SystemExit(f"✖ {name}: bbox 안에 블록이 없다 — 월드/좌표를 확인할 것")

    out = {
        "id": spec["uuid"],
        "name": name,
        "creator": "00000000-0000-0000-0000-000000000000",
        "created": spec["created"],
        "size": [x2 - x1 + 1, y2 - y1 + 1, z2 - z1 + 1],
        "blocks": blocks,
        "pilotSeat": [spec["pilot"][0] - ox, spec["pilot"][1] - oy, spec["pilot"][2] - oz],
        "passengerSeats": [[p[0] - ox, p[1] - oy, p[2] - oz] for p in spec["passengers"]],
        "speed": spec["speed"],
        "durationSeconds": spec["duration"],
        "cooldownSeconds": spec["cooldown"],
        "price": spec["price"],
    }

    os.makedirs(SHIPS, exist_ok=True)
    path = os.path.join(SHIPS, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    ys = [b["y"] for b in blocks]
    sails = sum(1 for b in blocks if b.get("animGroup") == "sail")
    print(f"✓ {path}")
    print(f"  블록 {len(blocks)}개 (물·공기 {skipped}칸 제외), 돛 {sails}개")
    print(f"  rel y {min(ys)}..{max(ys)}  → 흘수 {-min(ys)}칸 (소환 시 수면 아래 요구 깊이)")
    print(f"  조종석 {out['pilotSeat']}  탑승석 {out['passengerSeats']}")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "돛단배")
