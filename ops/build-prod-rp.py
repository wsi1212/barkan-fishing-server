"""메인 리소스팩 다이어트 — 접속 지연(팩 111MB) 해소용.

① betterhud 제외(이제 CraftEngine 팩이 제공한다)  -17.7MB
② 백업/잡동사니 제외(.bak/_prepad/backup/pf_reference)
③ 아이템 텍스처 한 변 128px 상한  -약 23MB
   ★아이템은 칸에서 16 GUI px(스케일3에서 48화면px)로 그려진다. 도감 물고기처럼
     칸 밖으로 커지는 것도 100화면px 안쪽이라 128이면 충분하고 256은 낭비다.
     원본(256/512)은 소스에 그대로 둔다 — 여기서만 줄인다(배포 단계 최적화).
④ PNG 무손실 재압축 + deflate 최대

원본 소스는 안 건드린다. 산출: barkan-resourcepack-slim.zip"""
import io, os, zipfile
from PIL import Image

RP = os.path.expanduser("~/development/barkan-resourcepack")
# 서버에만 있고 소스에 없던 파일들(누군가 박스에서 직접 넣은 것). 통째 교체 때 안 잃으려면
# 여기에 받아 두고 같이 굽는다. 지금은 소리 3개 + 보스바 스프라이트 3개.
EXTRA = os.path.expanduser("~/development/barkan-rp-extra")
OUT = "/tmp/barkan-resourcepack-slim.zip"
JUNK = (".bak-", "backup", "_prepad", "pf_reference", ".DS_Store", ".codex-backup")

def gather(root, base=""):
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if not any(j in d for j in JUNK)]
        for f in files:
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root)
            if any(j in rel for j in JUNK):
                continue
            yield rel.replace(os.sep, "/"), p

files = {}
for top in ("assets", "pack.mcmeta"):
    src = os.path.join(RP, top)
    if os.path.isdir(src):
        for rel, p in gather(src):
            files[f"{top}/{rel}"] = p
    elif os.path.isfile(src):
        files[top] = src
if os.path.isdir(EXTRA):
    for rel, p in gather(EXTRA):
        files.setdefault(rel, p)                 # 서버에만 있던 것 보강

png_before = png_after = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in sorted(files):
        p = files[name]
        data = open(p, "rb").read()
        if name.endswith(".png"):
            png_before += len(data)
            try:
                im = Image.open(io.BytesIO(data))
                cap = 128 if name.startswith("assets/minecraft/textures/item/") else None
                # 프레임 애니(.mcmeta 동반)는 세로로 이어 붙인 띠라 비율을 건드리면 깨진다
                if cap and f"{name}.mcmeta" not in files and max(im.size) > cap:
                    r = cap / max(im.size)
                    im = im.resize((max(1, round(im.width * r)), max(1, round(im.height * r))),
                                   Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, "PNG", optimize=True)
                if buf.tell() < len(data):
                    data = buf.getvalue()
            except Exception:
                pass
            png_after += len(data)
        z.writestr(name, data)

print(f"항목 {len(files)}")
print(f"PNG {png_before/1e6:.1f}MB → {png_after/1e6:.1f}MB ({100*(1-png_after/max(1,png_before)):.0f}% 절감)")
print(f"zip {os.path.getsize(OUT)/1e6:.1f}MB")
