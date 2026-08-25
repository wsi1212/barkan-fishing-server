#!/usr/bin/env python3
"""원저자 통합 리소스팩 zip → 메인 팩 병합 + 리듬 곡 분리 팩 산출.

## 왜 이 스크립트인가
원저자(Barkan)가 주는 `Barkan-ResourcePack-*.zip` 은 **체스 + 피아노 + 리듬이 한 덩어리**다.
통째로 얹으면 안 되는 이유가 셋이다.

1. **리듬 곡이 83MB** — 메인 팩(100MB)에 넣으면 183MB 가 되어 리듬을 안 하는 사람까지
   팩이 바뀔 때마다 다 받는다. 그래서 리듬 곡만 **별도 팩**으로 뽑는다.
2. **`art_easel.json` 은 체스 jar 과 한 몸** — 이젤 모델의 액자 구멍은
   `PaintingManager.EASEL_Y` 를 전제로 잡혀 있다. 팩만 새 걸로 갈면 그림이 0.5블록 어긋난다.
   그래서 **우리 것을 지킨다**(체스 jar 을 같이 올릴 때만 손댈 것).
3. **`sounds.json` 은 공용** — 통째 덮으면 우리 weather/bgm/ui/enhance 키가 날아간다.
   키 단위로 병합한다.

받은 zip 에서 매번 다시 뽑는다 — 사본을 고정하지 않는다.

## 소리는 재인코딩하지 않는다
2026-08-25 에 피아노를 모노로 내렸다가 "받은 곳이랑 소리가 다르다"는 지적을 받고 되돌렸다.
바이트 그대로 넣는다. (대가: 스테레오는 위치 음원이 아니라 거리 감쇠가 없다 — 알고 가는 선택)

사용:
    ops/sync-barkan-pack.py ~/Downloads/Barkan-ResourcePack-1.21.11.zip [--dry-run]
      → ~/development/barkan-resourcepack/  (리듬 곡 제외 전부)
      → /tmp/barkan-rhythm-pack.zip         (리듬 곡만, 별도 배포용)
    배포는 별도: ops/rp-deploy.sh <dev|prod>
"""
import argparse, hashlib, json, os, shutil, sys, zipfile

RP = os.path.expanduser("~/development/barkan-resourcepack")
RHYTHM_PREFIX = "assets/barkan/sounds/rhythm/"
RHYTHM_KEY = "rhythm."
OUT_RHYTHM = "/tmp/barkan-rhythm-pack.zip"
# ★메인 팩에서 우리 것을 지켜야 하는 파일 (업스트림 것으로 덮지 않는다)
KEEP_OURS = {
    # 이젤 모델은 체스 jar 의 PaintingManager.EASEL_Y 와 짝 — 한쪽만 갈면 그림이 어긋난다
    "assets/barkan/models/item/chess/art_easel.json",
}
EPOCH = (1980, 1, 1, 0, 0, 0)   # 결정적 zip — 내용이 같으면 sha1 도 같게

ap = argparse.ArgumentParser()
ap.add_argument("zip")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

if not os.path.isdir(RP):
    sys.exit(f"메인 리소스팩을 찾을 수 없다: {RP}")
z = zipfile.ZipFile(a.zip)
names = [n for n in z.namelist() if not n.endswith("/")]

main_files  = [n for n in names if n.startswith("assets") and not n.startswith(RHYTHM_PREFIX)
               and not n.endswith("sounds.json")]
rhythm_files = [n for n in names if n.startswith(RHYTHM_PREFIX)]
if not rhythm_files:
    print("⚠️ 리듬 곡이 zip 에 없다 — 리듬 팩은 만들지 않는다")

# ── sounds.json 분리 ────────────────────────────────────────────────────────
up_sounds = json.loads(z.read("assets/barkan/sounds.json"))
cur_path = os.path.join(RP, "assets/barkan/sounds.json")
cur = json.load(open(cur_path, encoding="utf-8"))
main_keys   = {k: v for k, v in up_sounds.items() if not k.startswith(RHYTHM_KEY)}
rhythm_keys = {k: v for k, v in up_sounds.items() if k.startswith(RHYTHM_KEY)}
lost = {k for k in cur if k not in up_sounds}          # 우리에만 있는 키 = 반드시 보존

added   = sorted(k for k in main_keys if k not in cur)
changed = sorted(k for k in main_keys if k in cur and cur[k] != main_keys[k])

# ── 메인 팩 쪽 변화 집계 ────────────────────────────────────────────────────
def sha(b): return hashlib.sha1(b).hexdigest()
new_files, mod_files, kept = [], [], []
for n in main_files:
    dst = os.path.join(RP, n)
    if n in KEEP_OURS and os.path.exists(dst):
        kept.append(n); continue
    if not os.path.exists(dst):
        new_files.append(n)
    elif sha(z.read(n)) != sha(open(dst, "rb").read()):
        mod_files.append(n)

print(f"메인 팩 ← 신규 {len(new_files)} / 갱신 {len(mod_files)} / 우리 것 유지 {len(kept)}")
for n in kept: print(f"   지킴 {n}")
print(f"sounds.json ← piano·chess 등 추가 {len(added)} / 갱신 {len(changed)} / 우리 전용 보존 {len(lost)}")
rsize = sum(z.getinfo(n).file_size for n in rhythm_files)
print(f"리듬 팩 → 곡 {len(rhythm_files)}개 · {rsize/1e6:.1f}MB · sounds 키 {len(rhythm_keys)}")
if a.dry_run:
    print("--dry-run: 아무것도 쓰지 않음"); sys.exit(0)

# ── 메인 팩 병합 ────────────────────────────────────────────────────────────
for n in new_files + mod_files:
    dst = os.path.join(RP, n)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as fh:
        fh.write(z.read(n))
cur.update(main_keys)                                   # 우리 전용 키는 그대로 남는다
with open(cur_path, "w", encoding="utf-8") as fh:
    json.dump(cur, fh, ensure_ascii=False, indent=2); fh.write("\n")
print(f"✅ 메인 팩 갱신 — sounds.json {len(cur)}키")

# ── 리듬 전용 팩 ────────────────────────────────────────────────────────────
if rhythm_files:
    meta = {"pack": {"description": "바르칸 리듬게임 음원", "min_format": 75, "max_format": 75}}
    with zipfile.ZipFile(OUT_RHYTHM, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        def put(name, data):
            zi = zipfile.ZipInfo(name, date_time=EPOCH)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            out.writestr(zi, data)
        put("pack.mcmeta", json.dumps(meta, ensure_ascii=False, indent=2))
        if os.path.exists(os.path.join(RP, "pack.png")):
            put("pack.png", open(os.path.join(RP, "pack.png"), "rb").read())
        put("assets/barkan/sounds.json", json.dumps(rhythm_keys, ensure_ascii=False, indent=2))
        for n in sorted(rhythm_files):
            put(n, z.read(n))
    h = sha(open(OUT_RHYTHM, "rb").read())
    print(f"✅ {OUT_RHYTHM} — {os.path.getsize(OUT_RHYTHM)/1e6:.1f}MB · sha1 {h}")
print("배포는 별도: ops/rp-deploy.sh <dev|prod>  (리듬 팩은 별도 호스팅)")
