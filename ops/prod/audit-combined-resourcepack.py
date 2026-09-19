import json,os,sys,zipfile,hashlib
MC=os.path.expanduser('~/mcserver')
BASE=f'{MC}/resourcepack-base/base.zip'; CE=f'{MC}/plugins/CraftEngine/generated/resource_pack.zip'
BH=f'{MC}/plugins/BetterHud/build.zip'; BM=f'{MC}/plugins/BetterModel/build.zip'
FIX=f'{MC}/plugins/CraftEngine/betterhud-26-1-fix'
EXTRA=f'{MC}/plugins/CraftEngine/resources/remove_shulker_head/resourcepack'
HOSTED='/var/www/barkan/barkan-furniture-scarecrow-20260912-1525.zip'   # 09-18까지 «잘 되던» CE 팩
COMBINED=sys.argv[1]
def zread(p):
    d={}
    if not os.path.exists(p): return d
    with zipfile.ZipFile(p) as z:
        for i in z.infolist():
            if not i.filename.endswith('/'): d[i.filename]=z.read(i.filename)
    return d
def dread(p):
    d={}
    for root,_,fns in os.walk(p) if os.path.isdir(p) else []:
        for fn in fns:
            full=os.path.join(root,fn); d[os.path.relpath(full,p)]=open(full,'rb').read()
    return d
b,c,h,m,fx,ex=zread(BASE),zread(CE),zread(BH),zread(BM),dread(FIX),dread(EXTRA)
comb=zread(COMBINED)
# 옛 CE 팩은 CE 보호팩이라 바이트를 못 읽는다(로컬헤더 훼손) — 이름만 쓴다.
hosted={}
if os.path.exists(HOSTED):
    with zipfile.ZipFile(HOSTED) as z: hosted={n:b'' for n in z.namelist() if not n.endswith('/')}
print(f"소스 파일수  base={len(b)} CE={len(c)} BH={len(h)} BM={len(m)} fix={len(fx)} extra={len(ex)}")
print(f"결합팩={len(comb)}  (옛 정상 CE팩={len(hosted)})\n")

def stacking(n): return ((('/font/' in n or '/lang/' in n or '/atlases/' in n) and n.endswith('.json')) or n.endswith('/sounds.json'))
# ① 존재 파리티: 옛 클라 뷰(main ∪ 옛 CE팩) 에 있던 경로가 결합팩에 다 있나
missing=[n for n in set(b)|set(hosted) if n not in comb and n not in ('pack.mcmeta','pack.png')]
print(f"① 존재 결손(옛 정상 뷰 대비): {len(missing)}"); [print("   -",n) for n in sorted(missing)[:20]]
# ② 우선순위 파리티: base<CE<BH<fix, stacking 은 병합
bad=[]
for n in set(comb)-{'pack.mcmeta','pack.png'}:
    if stacking(n): continue
    want=None
    for src in (b,c,h,fx,ex):
        if n in src: want=src[n] if src is not ex else (want if want is not None else src[n])
    if want is not None and comb[n]!=want: bad.append(n)
print(f"② 우선순위 불일치(base<CE<BH<fix 기준): {len(bad)}"); [print("   -",n) for n in sorted(bad)[:20]]
# ③ 세대 함정: CE 사본 vs 외부 원본(BH/BM) 바이트 차이
for name,src in (('BetterHud',h),('BetterModel',m)):
    diff=[n for n in src if n in c and c[n]!=src[n]]
    print(f"③ CE 안의 {name} 사본이 원본과 다른 파일: {len(diff)}")
    for n in sorted(diff)[:12]:
        w='결합팩=원본' if comb.get(n)==src[n] else ('결합팩=CE사본' if comb.get(n)==c[n] else '결합팩=제3의것')
        print(f"   - {n}  → {w}")
# ④ stacking 병합이 상위집합인가
for n in sorted(x for x in comb if stacking(x)):
    try: cj=json.loads(comb[n])
    except Exception: continue
    for src,label in ((b,'base'),(c,'CE'),(h,'BH')):
        if n not in src: continue
        try: sj=json.loads(src[n])
        except Exception: continue
        for key in ('providers','sources'):
            if isinstance(sj.get(key),list) and len(cj.get(key,[]))<len(sj[key]):
                print(f"④ 결손! {n} {key}: 결합 {len(cj.get(key,[]))} < {label} {len(sj[key])}")
        if isinstance(sj,dict) and not any(k in sj for k in ('providers','sources')):
            miss=[k for k in sj if k not in cj]
            if miss: print(f"④ 결손! {n}: {label} 키 {len(miss)}개 빠짐")
print("④ stacking 병합 검사 완료")
# ⑤ mcmeta / 오버레이
mm=json.loads(comb['pack.mcmeta']); ovs=mm.get('overlays',{}).get('entries',[])
dirs={n.split('/',1)[0] for n in comb if '/' in n}
print(f"⑤ mcmeta min={mm['pack'].get('min_format')} max={mm['pack'].get('max_format')} 오버레이 {len(ovs)}개, 누락 {[e['directory'] for e in ovs if e['directory'] not in dirs]}")
sh=[n for n in comb if '/shaders/core/' in n]
print(f"⑤ 셰이더 {len(sh)}개 · BH폰트 {len([n for n in comb if 'betterhud/font/' in n])}개")
