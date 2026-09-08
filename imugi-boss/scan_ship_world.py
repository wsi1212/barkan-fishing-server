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
#  ★origin 의 y 는 **갑판 바닥칸**으로 잡는다 — 즉 «걸어다니는 면이 rel 0» 이 되게.
#    ShipCollider.findWaterSurface 가 「물이면서 위가 공기인 y」**+1**(= 수면 위 첫 공기칸)을
#    돌려주고 그게 소환 중심 Y 다. 그래서 갑판을 rel 0 으로 두면 갑판칸이 수면 위 첫 칸에 놓여
#    **갑판 바닥면이 정확히 수면 위에 올라앉고**(발이 물에 안 잠긴다) 그 아래 선체·용골이 잠긴다.
#    ★지어 놓은 좌표를 그대로 origin 으로 쓰면 안 된다 — 그 배는 갑판칸이 «수면 칸» 이라
#    물이 갑판 바닥과 같은 높이다(반쯤 잠긴 꼴). 장식으로는 몰라도 타는 배로는 못 쓴다.
#    minRelY 가 깊을수록 소환에 필요한 수심이 늘어난다(floatsAt 이 minRelY 바로 아래를 물로 요구).
#
#  ★rot = 월드→배로컬 90° 회전 횟수(위에서 봤을 때 시계방향, 동→남→서→북).
#    **배의 선수(뱃머리)는 배 로컬 +Z 여야 한다** — ShipTickTask.moveByVelocity 가 yaw 0 에서
#    (dx,dz)=(0,+vel) 로 나아가기 때문이다. 월드에 X축으로 지어 뒀으면 rot=1 로 돌려 뜬다
#    (rot=1 은 월드 +X 를 로컬 +Z 로 보낸다). 좌표뿐 아니라 **blockstate 도 같이 돌린다**
#    (facing/axis/fence·wall 의 north|south|east|west/rotation) — 안 돌리면 계단·트랩도어가
#    엉뚱한 방향을 보고 돛 두께축(scale)이 뒤집혀 돛이 슬랫으로 잘려 보인다.
#
#  ★max_kmh = 최고 속도(km/h). 배 HUD 가 km/h 로 찍으므로 저장도 km/h 로 한다.
#    노트로 말할 땐 ×1.852 로 환산해 넣을 것.
#  ★cash = 캐시 전용 상품이면 캐시가(그때 price 는 0). 한 배에 두 통화를 같이 붙이지 않는다.
PRESETS = {
    "돛단배": dict(
        world=os.path.join(SERVER, "world"),
        bbox=(415, 58, 1015, 421, 70, 1027),   # prod 스폰항 앞바다에 손으로 지은 소형 범선
        origin=(418, 60, 1021),                # x=용골 중심, y=갑판 바닥칸, z=선체 중앙
        pilot=(418, 61, 1023),                 # 선미 조종석
        passengers=[(418, 61, 1018)],          # 선수 탑승석
        max_kmh=30,                            # 2026-09-08 유저 지정
        # ★원화로 남긴다 — 튜토리얼 「튜토_배2」(action|배구매)의 유일한 구매 경로다.
        #   캐시 전용으로 돌리면 캐시가 없는 신규가 튜토에서 영구히 막힌다.
        duration=90, cooldown=60, price=10000,
        created=1788700000000,
        uuid="6b1f2d4a-8c33-5e17-9a20-0d1c7f4b3e88",
    ),
    # temple_show 전시월드에 손으로 지어 둔 바이킹 롱쉽. 장축이 X(용머리가 +X 쪽 x=500,
    # 반대쪽 x=469 는 단순 선미기둥)라 rot=1 로 돌려 선수를 로컬 +Z 로 맞춘다.
    "바이킹롱쉽": dict(
        world=os.path.join(SERVER, "temple_show"),
        bbox=(469, 158, 351, 500, 183, 363),
        origin=(484, 159, 357),                # x=돛대(장축 중앙), y=갑판 바닥칸, z=선체 중앙선
        rot=1,                                 # 월드 +X(용머리) → 배 로컬 +Z(선수)
        pilot=(490, 160, 357),                 # 유저 지정
        passengers=[(487, 160, 357), (481, 160, 357),
                    (478, 160, 357), (475, 160, 357)],   # 노꾼 벤치 4석 (유저 지정)
        max_kmh=40,                            # 2026-09-08 유저 지정
        # 캐시 전용 상품(price 0). 10,000 캐시 = 캐시샵 「배스킨」 3종과 같은 등급.
        duration=180, cooldown=90, price=0, cash=10000,
        created=1788800000000,
        uuid="2f7c9e51-4b6a-5d38-8e14-7a3f0c92b6d1",
    ),
}


# ── 월드→배로컬 90° 회전 (위에서 봤을 때 시계방향: 동→남→서→북) ──────────────
_CW = {"north": "east", "east": "south", "south": "west", "west": "north"}
_AXIS = {"x": "z", "z": "x", "y": "y"}


def rot_xz(dx, dz, k):
    """월드 상대좌표 → 배 로컬 상대좌표. k=1 이면 (+X → +Z), (+Z → −X)."""
    for _ in range(k % 4):
        dx, dz = -dz, dx
    return dx, dz


def rot_state(data, k):
    """blockstate 를 같은 방향으로 k×90° 돌린다."""
    k %= 4
    if k == 0 or "[" not in data:
        return data
    base, rest = data.split("[", 1)
    props = dict(kv.split("=", 1) for kv in rest.rstrip("]").split(","))
    for _ in range(k):
        new = {}
        for name, val in props.items():
            if name == "facing":
                new[name] = _CW.get(val, val)          # up/down 은 그대로
            elif name == "axis":
                new[name] = _AXIS[val]
            elif name == "rotation":                    # 표지판/배너 0~15 (남=0, 시계방향)
                new[name] = str((int(val) + 4) % 16)
            elif name in _CW:                           # 울타리·담장·철창의 방향별 값
                new[_CW[name]] = val
            else:
                new[name] = val                         # half·shape·type·open·face… 는 회전 불변
        props = new
    return base + "[" + ",".join(f"{k2}={v}" for k2, v in sorted(props.items())) + "]"


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
    rot = spec.get("rot", 0) % 4
    world = anvil.region_blocks(spec["world"], x1, y1, z1, x2, y2, z2)

    blocks, skipped = [], 0
    for (x, y, z), data in sorted(world.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
        base = data.split("[")[0]
        if base in SKIP or base in ("minecraft:water", "minecraft:bubble_column"):
            skipped += 1
            continue
        # 물속에서 뜬 배라 waterlogged 가 켜져 있으면 소환 후에도 물을 달고 다닌다
        data = data.replace("waterlogged=true", "waterlogged=false")
        data = rot_state(data, rot)
        # ★분류는 «회전 뒤» 에 한다 — auto_classify 가 돌려주는 돛 두께축 [1,1,0.15] 은
        #   이미 배 로컬(선수미축=Z)로 얇다는 뜻이라 다시 돌리면 안 된다.
        nc, ag, sc = auto_classify(data)
        rx, rz = rot_xz(x - ox, z - oz, rot)
        b = {"x": rx, "y": y - oy, "z": rz, "data": data}
        if nc: b["noCollision"] = True
        if ag: b["animGroup"] = ag
        if sc: b["scale"] = sc
        blocks.append(b)
    blocks.sort(key=lambda b: (b["y"], b["z"], b["x"]))

    if not blocks:
        raise SystemExit(f"✖ {name}: bbox 안에 블록이 없다 — 월드/좌표를 확인할 것")

    def seat(p):
        sx, sz = rot_xz(p[0] - ox, p[2] - oz, rot)
        return [sx, p[1] - oy, sz]

    sx, sz = (x2 - x1 + 1, z2 - z1 + 1)
    if rot % 2: sx, sz = sz, sx        # 90°/270° 는 장축이 바뀐다
    out = {
        "id": spec["uuid"],
        "name": name,
        "creator": "00000000-0000-0000-0000-000000000000",
        "created": spec["created"],
        "size": [sx, y2 - y1 + 1, sz],
        "blocks": blocks,
        "pilotSeat": seat(spec["pilot"]),
        "passengerSeats": [seat(p) for p in spec["passengers"]],
        "maxKmh": spec["max_kmh"],
        "durationSeconds": spec["duration"],
        "cooldownSeconds": spec["cooldown"],
        "price": spec["price"],
        "cashPrice": spec.get("cash", 0),
    }

    os.makedirs(SHIPS, exist_ok=True)
    path = os.path.join(SHIPS, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    ys = [b["y"] for b in blocks]
    zs = [b["z"] for b in blocks]
    sails = sum(1 for b in blocks if b.get("animGroup") == "sail")
    print(f"✓ {path}")
    print(f"  블록 {len(blocks)}개 (물·공기 {skipped}칸 제외), 돛 {sails}개, 회전 {rot*90}°")
    print(f"  rel y {min(ys)}..{max(ys)}  → 흘수 {-min(ys)}칸 (소환 시 수면 아래 요구 깊이)")
    print(f"  rel z {min(zs)}..{max(zs)}  (선수=+Z 쪽 {max(zs)}, 선미={min(zs)})")
    print(f"  최고속도 {spec['max_kmh']} km/h ({spec['max_kmh']/1.852:.1f}노트)")
    print(f"  가격 {spec['price']:,}원" if not spec.get("cash")
          else f"  가격 {spec['cash']:,} 캐시 (캐시 전용)")
    print(f"  조종석 {out['pilotSeat']}  탑승석 {out['passengerSeats']}")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "돛단배")
