#!/usr/bin/env bash
# 메인팩과 CraftEngine의 표준(unprotected) 생성팩을 한 파일로 합친다.
# 서버가 꺼져 있지 않아도 안전하다: Paper는 다음 부팅 때만 server.properties를 읽는다.
set -euo pipefail

MC=${MC_ROOT:-$HOME/mcserver}
PROPS="$MC/server.properties"
CE="$MC/plugins/CraftEngine/generated/resource_pack.zip"
BH="$MC/plugins/BetterHud/build.zip"
# ★CE 는 remove_shulker_head 팩의 2개 파일을 generated 에 안 싣는다(보호팩에만 들어간다).
#   가구가 셜커 머리를 숨기는 데 쓰는 파일이라 빠지면 머리가 보인다.
CE_EXTRA="$MC/plugins/CraftEngine/resources/remove_shulker_head/resourcepack"
# ★26.1+ 클라용 셰이더 덮어쓰기(betterhud-26-1-fix.sh 가 build.zip 에서 뽑아 둔 현재 세대).
CE_FIX="$MC/plugins/CraftEngine/betterhud-26-1-fix"
CE_CFG="$MC/plugins/CraftEngine/config.yml"
WEB=${WEBROOT:-/var/www/barkan}
# 공개 주소 접두와 설치 권한은 환경별로 다르다(prod=Caddy+sudo, dev=로컬 8801+권한 없음).
PUBBASE=${PUBBASE:-https://barkan.kr}
SUDO=${SUDO-sudo}
BASE_DIR="$MC/resourcepack-base"
BASE="$BASE_DIR/base.zip"
BASE_META="$BASE_DIR/base.json"
STATE="$BASE_DIR/combined.json"

die(){ echo "combined-rp: $*" >&2; exit 1; }
sha(){ sha1sum "$1" | awk '{print $1}'; }
prop(){ sed -n "s/^$1=//p" "$PROPS" | head -1; }

[ -s "$CE" ] || die "표준 CraftEngine 팩이 없다: $CE"
unzip -tqq "$CE" >/dev/null || die "표준 CraftEngine 팩 ZIP 검증 실패"
mkdir -p "$BASE_DIR"
url=$(prop resource-pack | sed 's/\\//g')
want=$(prop resource-pack-sha1 | tr '[:upper:]' '[:lower:]')

# fetch-resourcepack이 새 GitHub 릴리스를 가리키면 그 파일을 다음 부팅용 원본으로 저장한다.
if [[ "$url" == https://github.com/* ]]; then
  t=$(mktemp "$BASE_DIR/base.XXXXXX.zip")
  trap 'rm -f "$t"' EXIT
  curl -fLsS --retry 3 --connect-timeout 15 --max-time 600 "$url" -o "$t" || die "메인팩 다운로드 실패"
  [ "$(sha "$t")" = "$want" ] || die "메인팩 SHA1 불일치"
  unzip -tqq "$t" >/dev/null || die "메인팩 ZIP 검증 실패"
  mv "$t" "$BASE"
  python3 - "$BASE_META" "$url" "$want" <<'PY'
import json, os, sys
p,u,s=sys.argv[1:]; t=p+'.tmp'
open(t,'w').write(json.dumps({'url':u,'sha1':s})+'\n'); os.replace(t,p)
PY
  trap - EXIT
fi
[ -s "$BASE" ] && [ -s "$BASE_META" ] || die "메인팩 원본 캐시 없음"
base_sha=$(sha "$BASE"); ce_sha=$(sha "$CE")
[ -s "$BH" ] && ce_sha="$ce_sha-$(sha "$BH")"
python3 - "$BASE_META" "$base_sha" <<'PY' || die "메인팩 캐시 SHA 메타데이터 불일치"
import json,sys
assert json.load(open(sys.argv[1]))['sha1'] == sys.argv[2]
PY

combined=""
if [ -s "$STATE" ]; then
  combined=$(python3 - "$STATE" "$base_sha" "$ce_sha" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1])); print(d['combinedSha1'] if d['baseSha1']==sys.argv[2] and d['ceSha1']==sys.argv[3] else '')
except Exception: pass
PY
)
fi
target=""
if [[ "$combined" =~ ^[0-9a-f]{40}$ ]] && [ -f "$WEB/barkan-resourcepack-combined-$combined.zip" ] && [ "$(sha "$WEB/barkan-resourcepack-combined-$combined.zip")" = "$combined" ]; then
  target="$WEB/barkan-resourcepack-combined-$combined.zip"
else
  t=$(mktemp "$BASE_DIR/combined.XXXXXX.zip")
  trap 'rm -f "$t"' EXIT
  python3 - "$BASE" "$CE" "$t" "${BH:-}" "${CE_EXTRA:-}" "${CE_FIX:-}" <<'PY'
import json,os,sys,zipfile
from pathlib import PurePosixPath
base,ce,out=sys.argv[1:4]
bh=sys.argv[4] if len(sys.argv)>4 else ''
extra=sys.argv[5] if len(sys.argv)>5 else ''
fix=sys.argv[6] if len(sys.argv)>6 else ''
def safe(n):
 p=PurePosixPath(n); return not p.is_absolute() and '..' not in p.parts and not n.endswith('/')
# ★팩 «스택»에서는 안 덮이고 «합쳐지는» 파일들이 있다 — 폰트 정의·lang·sounds·atlases.
#   3개 팩을 따로 보내던 시절엔 클라가 이걸 합쳐 줬다(메인팩의 글리프 provider + CE 것).
#   한 파일로 합치면서 그냥 덮어써서 메인팩의 provider 가 사라졌고, 그게 «폰트가 안 바뀌고
#   메뉴(글리프 이미지)가 안 보이는» 증상이었다(2026-09-19). 그래서 여기서 직접 합친다.
def stacking(n):
 # ★betterhud 자산은 «합치면» 안 된다 — 세대마다 통째로 새로 생성되는 파일이라
 #   옛 세대 provider 가 섞이면 없는 텍스처를 가리킨다. BetterHud 것으로 통째 교체한다.
 if n.startswith('assets/betterhud/'): return False
 return (('/font/' in n and n.endswith('.json')) or ('/lang/' in n and n.endswith('.json'))
         or n.endswith('/sounds.json') or ('/atlases/' in n and n.endswith('.json')))
def merge_json(old,new):
 try:
  a=json.loads(old); b=json.loads(new)
 except Exception:
  return new
 if isinstance(a,dict) and isinstance(b,dict):
  for key in ('providers','sources'):   # 배열 이어붙이기 (뒤에 오는 팩이 우선)
   if isinstance(a.get(key),list) and isinstance(b.get(key),list):
    out=dict(a); out[key]=a[key]+b[key]; out.update({k:v for k,v in b.items() if k!=key})
    return json.dumps(out,ensure_ascii=False).encode()
  out=dict(a); out.update(b)            # lang·sounds 는 키 병합
  return json.dumps(out,ensure_ascii=False).encode()
 return new
def put(files,name,data):
 if name in files and stacking(name): files[name]=merge_json(files[name],data)
 else: files[name]=data
files={}
with zipfile.ZipFile(base) as z:
 for i in z.infolist():
  if safe(i.filename): files[i.filename]=z.read(i.filename)
base_meta=json.loads(files['pack.mcmeta'])
# ★CE 팩은 assets/ 만이 아니다 — 오버레이 디렉터리(betterhud_*, bettermodel_modern, ce_overlay_*)에
#   버전별 정본이 들어 있고 BetterHud 의 코어 셰이더는 «오버레이에만» 있다. assets/ 만 복사하면
#   클라가 받는 팩에 셰이더가 0개가 되어 HUD 가 통째로 깨진다(2026-09-19 실측, 26.2 클라 제보).
# ★BetterHud 자산은 CE 팩에 «부분만» 병합돼 온다(2026-09-19 실측: 폰트 1338개 중 62개).
#   빠지는 1276개가 HUD·NPC 대화창 글리프라 폰트가 통째로 안 바뀐다. 그래서 build.zip 을
#   직접 얹는다. 순서는 BH 먼저·CE 나중 — CE 의 betterhud-26-1-fix 가 BH 의 26_1 셰이더를
#   덮어야 하기 때문(반대로 하면 26.1+ 클라 HUD 가 화면 밖으로 날아간다).
with zipfile.ZipFile(ce) as z:
 ce_meta=json.loads(z.read('pack.mcmeta'))
 for i in z.infolist():
  if safe(i.filename) and i.filename!='pack.mcmeta' and i.filename!='pack.png':
   put(files,i.filename,z.read(i.filename))
# ★BH 는 CE «뒤»에 얹는다 — CE 안의 BetterHud 사본은 한 세대 뒤처진다(2026-09-19 실측:
#   CE 것은 셰이더 좌표표 case 2개, build.zip 은 3개 → 오른쪽 위 HUD 가 화면 밖으로 날아갔다).
if bh:
 with zipfile.ZipFile(bh) as z:
  for i in z.infolist():
   if safe(i.filename) and i.filename not in ('pack.mcmeta','pack.png'):
    put(files,i.filename,z.read(i.filename))
# 26.1+ 전용 셰이더만 CE 의 fix 폴더가 최종 승자다(BH 가 26_1 자리에 주는 건 1.21.6 용이라 깨진다).
if fix and os.path.isdir(fix):
 for root,_,fns in os.walk(fix):
  for fn in fns:
   full=os.path.join(root,fn); rel=os.path.relpath(full,fix)
   if safe(rel): files[rel]=open(full,'rb').read()
# CE 가 generated 에서 빠뜨린 리소스팩 트리를 «없는 경로만» 채운다(덮어쓰지 않는다).
if extra and os.path.isdir(extra):
 for root,_,fns in os.walk(extra):
  for fn in fns:
   full=os.path.join(root,fn); rel=os.path.relpath(full,extra)
   if safe(rel): files.setdefault(rel,open(full,'rb').read())
# CE 의 overlays 선언을 그대로 승계하고, 팩 적용범위 상한도 CE 쪽까지 넓힌다.
ovs=ce_meta.get('overlays',{}).get('entries',[])
def hi(v,d):
 x=v.get(d)
 return x[0] if isinstance(x,list) else (x if isinstance(x,int) else None)
base_max=hi(base_meta['pack'],'max_format') or base_meta['pack'].get('pack_format')
ce_max=hi(ce_meta['pack'],'max_format') or ce_meta['pack'].get('pack_format')
# CE 가 선언한 상한(88)만 따르면 그보다 새 클라(26.2 등)가 «범위 밖» 이 된다.
# 오버레이가 커버하는 상한까지 올리되, ce_overlay_* 의 1000 같은 «무한» 표기는 99 로 자른다.
cand=[x for x in (base_max,ce_max) if x]+[hi(e,'max_format') or 0 for e in ce_meta.get('overlays',{}).get('entries',[])]
newmax=max(x for x in cand if x and x<=99)
base_meta['pack']['max_format']=newmax
if isinstance(base_meta['pack'].get('min_format'),int):
 pass
if ovs:
 base_meta['overlays']={'entries':ovs}
# 선언한 오버레이 디렉터리가 실제로 들어갔는지 검산 (빈 선언은 클라가 팩 전체를 거부한다)
dirs={n.split('/',1)[0] for n in files if '/' in n}
missing=[e['directory'] for e in ovs if e['directory'] not in dirs]
assert not missing, f"오버레이 디렉터리 누락: {missing}"
shaders=[n for n in files if '/shaders/core/' in n]
assert shaders, "코어 셰이더가 0개다 — BetterHud HUD 가 깨진다"
for fn in ('assets/barkan/font/gui.json','assets/minecraft/font/default.json'):
 if fn in files:
  with zipfile.ZipFile(base) as z:
   if fn in z.namelist():
    b0=len(json.loads(z.read(fn)).get('providers',[])); b1=len(json.loads(files[fn]).get('providers',[]))
    assert b1>=b0, f"{fn} provider 결손: {b1}<{b0} — 메뉴 글리프가 사라진다"
if bh:
 with zipfile.ZipFile(bh) as z:
  ref=[n for n in z.namelist() if n.endswith('betterhud_1_21_6/assets/minecraft/shaders/core/rendertype_text.vsh')]
  if ref:
   want_cases=z.read(ref[0]).count(b'case ')
   for n,v in files.items():
    if n.endswith('/shaders/core/rendertype_text.vsh') and n.startswith('betterhud_'):
     assert v.count(b'case ')==want_cases, f"{n}: HUD 좌표표 세대 불일치({v.count(b'case ')} vs {want_cases}) — HUD 가 화면 밖으로 날아간다"
fonts=[n for n in files if 'betterhud/font/' in n]
if bh:
 with zipfile.ZipFile(bh) as z: want=len([n for n in z.namelist() if 'betterhud/font/' in n])
 assert len(fonts)>=want, f"BetterHud 폰트 결손: {len(fonts)}/{want} — HUD·메뉴 글리프가 안 나온다"
files['pack.mcmeta']=json.dumps(base_meta,ensure_ascii=False).encode()
print(f"  결합: 파일 {len(files)}개 · 오버레이 {len(ovs)}개 · 셰이더 {len(shaders)}개 · BH폰트 {len(fonts)}개 · max_format={newmax}",file=sys.stderr)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for n in sorted(files):
  i=zipfile.ZipInfo(n,date_time=(1980,1,1,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED; i.external_attr=0o644<<16
  z.writestr(i,files[n])
PY
  unzip -tqq "$t" >/dev/null || die "결합팩 ZIP 검증 실패"
  combined=$(sha "$t"); target="$WEB/barkan-resourcepack-combined-$combined.zip"
  $SUDO install -d -m 0755 "$WEB"
  $SUDO install -m 0644 "$t" "$target.tmp"
  $SUDO mv "$target.tmp" "$target"
  [ "$(sha "$target")" = "$combined" ] || die "공개 결합팩 SHA1 불일치"
  python3 - "$STATE" "$base_sha" "$ce_sha" "$combined" <<'PY'
import json,os,sys
p,b,c,h=sys.argv[1:]; t=p+'.tmp'; open(t,'w').write(json.dumps({'baseSha1':b,'ceSha1':c,'combinedSha1':h})+'\n'); os.replace(t,p)
PY
  trap - EXIT
fi

public="$PUBBASE/$(basename "$target")"
curl -fLsS --max-time 300 "$public" -o /tmp/combined-rp-check.zip || die "공개 결합팩 다운로드 실패"
[ "$(sha /tmp/combined-rp-check.zip)" = "$combined" ] || die "공개 결합팩 SHA1 불일치"
python3 - "$PROPS" "$public" "$combined" <<'PY'
import os,sys,uuid
p,u,s=sys.argv[1:]; pid=str(uuid.uuid5(uuid.NAMESPACE_URL,'barkan-resourcepack\n'+u+'\n'+s)); out=[]; a=b=c=False
for line in open(p):
 if line.startswith('resource-pack='): out.append('resource-pack='+u.replace(':','\\:',1)+'\n'); a=True
 elif line.startswith('resource-pack-sha1='): out.append('resource-pack-sha1='+s+'\n'); b=True
 elif line.startswith('resource-pack-id='): out.append('resource-pack-id='+pid+'\n'); c=True
 else: out.append(line)
assert a and b
if not c: out.append('resource-pack-id='+pid+'\n')
t=p+'.combined.tmp'; open(t,'w').writelines(out); os.replace(t,p)
PY
# 다음 부팅부터만 CE의 별도 로그온 전송을 중단한다.
python3 - "$CE_CFG" <<'PY'
import os,sys
p=sys.argv[1:][0]; out=[]; inside=False
for line in open(p):
 if line.startswith('  delivery:'): inside=True
 elif inside and line.startswith('  ') and not line.startswith('    '): inside=False
 if inside and line.startswith('    send-on-join:'): line='    send-on-join: false\n'
 if inside and line.startswith('    resend-on-upload:'): line='    resend-on-upload: false\n'
 out.append(line)
t=p+'.combined.tmp'; open(t,'w').writelines(out); os.replace(t,p)
PY
echo "combined-rp: ready $combined"
