#!/usr/bin/env python3
"""결합 리소스팩 전수 감사 — «클라가 예전에 받던 것» 대비 무엇이 사라졌/뒤처졌는지 본다.

왜 있나 (2026-09-19): 메인팩+CE팩을 한 파일로 합치면서 세 번 연속으로 조용히 깨졌다.
  ① CE 오버레이 디렉터리를 통째로 버려 코어 셰이더가 0개 → HUD 전멸
  ② BetterHud 폰트 1338개 중 62개만 실려 메뉴 글리프가 안 나옴
  ③ 팩 «스택»에서 합쳐지는 파일(font/lang/sounds/atlases)을 덮어써 gui.json provider 645→2
  ④ CE 안의 BetterHud 사본이 한 세대 뒤처져 셰이더 좌표표가 2 vs 3 → 오른쪽 위 HUD 실종
셋 다 서버 로그·배포 리포트는 «성공» 이었다. 사람 눈으로만 잡히는 걸 기계가 잡게 한다.

  audit-combined-resourcepack.py <pack.zip>                 # 사람이 읽는 리포트
  audit-combined-resourcepack.py --gate <pack.zip>          # 문제 있으면 exit 1 (배포 게이트)
  audit-combined-resourcepack.py --save-baseline <pack.zip> # 「이 팩은 실측으로 정상」 기준선 저장
기준선은 ~/mcserver/resourcepack-base/known-good.json — **인게임에서 눈으로 확인한 팩만** 저장할 것.
"""
import json,os,sys,zipfile

MC=os.environ.get('MC_ROOT',os.path.expanduser('~/mcserver'))
BASE=f'{MC}/resourcepack-base/base.zip'; CE=f'{MC}/plugins/CraftEngine/generated/resource_pack.zip'
BH=f'{MC}/plugins/BetterHud/build.zip';  BM=f'{MC}/plugins/BetterModel/build.zip'
FIX=f'{MC}/plugins/CraftEngine/betterhud-26-1-fix'
EXTRA=f'{MC}/plugins/CraftEngine/resources/remove_shulker_head/resourcepack'
BASELINE=os.environ.get('RP_BASELINE',f'{MC}/resourcepack-base/known-good.json')

def zread(p):
    d={}
    if not os.path.exists(p): return d
    with zipfile.ZipFile(p) as z:
        for i in z.infolist():
            if not i.filename.endswith('/'):
                try: d[i.filename]=z.read(i.filename)
                except Exception: d[i.filename]=None   # CE 보호팩은 바이트를 못 읽는다(이름만)
    return d
def dread(p):
    d={}
    if os.path.isdir(p):
        for root,_,fns in os.walk(p):
            for fn in fns:
                full=os.path.join(root,fn); d[os.path.relpath(full,p)]=open(full,'rb').read()
    return d
def stacking(n):
    if n.startswith('assets/betterhud/'): return False
    return ((('/font/' in n or '/lang/' in n or '/atlases/' in n) and n.endswith('.json'))
            or n.endswith('/sounds.json'))
def counts(comb):
    def providers(n):
        try: return len(json.loads(comb[n]).get('providers',[]))
        except Exception: return 0
    mm=json.loads(comb['pack.mcmeta'])
    return {
      'files':len(comb),
      'shaders':len([n for n in comb if '/shaders/core/' in n]),
      'bh_fonts':len([n for n in comb if 'betterhud/font/' in n]),
      'overlays':len(mm.get('overlays',{}).get('entries',[])),
      'gui_providers':providers('assets/barkan/font/gui.json'),
      'default_providers':providers('assets/minecraft/font/default.json'),
      'max_format':mm['pack'].get('max_format'),
    }

def audit(pack):
    b,c,h,m,fx,ex=zread(BASE),zread(CE),zread(BH),zread(BM),dread(FIX),dread(EXTRA)
    comb=zread(pack); problems=[]; report=[]
    report.append(f"소스 base={len(b)} CE={len(c)} BH={len(h)} BM={len(m)} fix={len(fx)} extra={len(ex)} → 결합팩={len(comb)}")

    # ① 기준선(마지막으로 «눈으로 확인된» 팩) 대비 파일 결손
    if os.path.exists(BASELINE):
        kg=json.load(open(BASELINE))
        miss=[n for n in kg['files'] if n not in comb]
        report.append(f"① 기준선({kg.get('sha1','?')[:12]}) 대비 결손: {len(miss)}")
        if miss: problems.append(f"기준선 대비 파일 {len(miss)}개 결손 (예: {miss[:3]})")
        for k,v in kg['counts'].items():
            now=counts(comb).get(k)
            if isinstance(v,int) and isinstance(now,int) and now<v:
                problems.append(f"{k} 감소: {v} → {now}")
    else:
        report.append("① 기준선 없음 — --save-baseline 로 정상 확인된 팩을 한 번 저장할 것")

    # ② 우선순위: base < CE < BH < fix (stacking 은 병합이라 제외)
    bad=[]
    for n,v in comb.items():
        if n in ('pack.mcmeta','pack.png') or stacking(n) or v is None: continue
        want=None
        for src in (b,c,h,fx):
            if n in src and src[n] is not None: want=src[n]
        if n not in b and n not in c and n not in h and n not in fx and n in ex: want=ex[n]
        if want is not None and v!=want: bad.append(n)
    report.append(f"② 우선순위 불일치: {len(bad)}")
    if bad: problems.append(f"우선순위 불일치 {len(bad)}개 (예: {bad[:3]})")

    # ③ 세대 함정: CE 사본이 원본(BH/BM)과 다를 때 결합팩은 «원본»을 실어야 한다
    for name,src in (('BetterHud',h),('BetterModel',m)):
        # fix 폴더가 주는 경로는 «의도된» 덮어쓰기라 원본과 달라야 정상이다.
        stale=[n for n in src if n in c and src[n] is not None and c[n] is not None
               and c[n]!=src[n] and n not in ('pack.mcmeta','pack.png') and n not in fx
               and comb.get(n) is not None and comb.get(n)!=src[n]]
        diff=len([n for n in src if n in c and c[n]!=src[n]])
        report.append(f"③ CE 사본 vs {name} 원본 차이 {diff}개 · 그중 결합팩이 옛 사본을 실은 것 {len(stale)}")
        if stale: problems.append(f"{name} 세대 뒤처짐 {len(stale)}개 (예: {stale[:3]})")

    # ③-b fix 폴더는 결합팩에 그대로 들어갔나 + 그 자체가 현재 세대인가
    for n,v in fx.items():
        if comb.get(n)!=v: problems.append(f"26-1-fix 미적용: {n}")
        ref6=n.replace('betterhud_26_1/','betterhud_1_21_6/')
        if ref6 in h and h[ref6].count(b'case ')!=v.count(b'case '):
            problems.append(f"26-1-fix 가 낡았다: {n} (case {v.count(b'case ')} vs build.zip {h[ref6].count(b'case ')}) → betterhud-26-1-fix.sh 재실행")

    # ④ 셰이더 좌표표 세대 (HUD 가 화면 밖으로 날아가는 그 증상)
    ref=[n for n in h if n.endswith('betterhud_1_21_6/assets/minecraft/shaders/core/rendertype_text.vsh')]
    if ref:
        want=h[ref[0]].count(b'case ')
        for n,v in comb.items():
            if n.startswith('betterhud_') and n.endswith('/shaders/core/rendertype_text.vsh'):
                if v.count(b'case ')!=want:
                    problems.append(f"{n} 좌표표 세대 불일치 {v.count(b'case ')} vs {want}")
        report.append(f"④ 셰이더 좌표표 case={want} 기준 검사 완료")

    # ⑤ stacking 병합이 각 소스의 상위집합인가
    lost=0
    for n,v in comb.items():
        if not stacking(n) or v is None: continue
        try: cj=json.loads(v)
        except Exception: continue
        for src in (b,c,h):
            if n not in src or src[n] is None: continue
            try: sj=json.loads(src[n])
            except Exception: continue
            for key in ('providers','sources'):
                if isinstance(sj.get(key),list) and len(cj.get(key,[]))<len(sj[key]):
                    problems.append(f"{n} {key} 결손 {len(cj.get(key,[]))}<{len(sj[key])}"); lost+=1
            if isinstance(sj,dict) and not any(k in sj for k in ('providers','sources')):
                miss=[k for k in sj if k not in cj]
                if miss: problems.append(f"{n} 키 {len(miss)}개 결손"); lost+=1
    report.append(f"⑤ stacking 병합 결손: {lost}")

    # ⑥ mcmeta·오버레이 실재
    mm=json.loads(comb['pack.mcmeta']); ovs=mm.get('overlays',{}).get('entries',[])
    dirs={n.split('/',1)[0] for n in comb if '/' in n}
    absent=[e['directory'] for e in ovs if e['directory'] not in dirs]
    if absent: problems.append(f"선언만 되고 없는 오버레이: {absent}")
    cnt=counts(comb)
    report.append(f"⑥ mcmeta min={mm['pack'].get('min_format')} max={cnt['max_format']} 오버레이 {cnt['overlays']}(누락 {len(absent)})")
    report.append(f"   셰이더 {cnt['shaders']} · BH폰트 {cnt['bh_fonts']} · gui.json provider {cnt['gui_providers']} · default {cnt['default_providers']}")
    return report,problems,counts(comb)

def main():
    a=sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    if a[0]=='--save-baseline':
        pack=a[1]; comb=zread(pack)
        import hashlib; sha=hashlib.sha1(open(pack,'rb').read()).hexdigest()
        json.dump({'sha1':sha,'files':sorted(comb),'counts':counts(comb)},open(BASELINE,'w'))
        print(f"기준선 저장: {BASELINE} ({sha[:12]}, 파일 {len(comb)})"); return
    gate = a[0]=='--gate'
    pack = a[1] if gate else a[0]
    report,problems,_=audit(pack)
    for r in report: print(r)
    if problems:
        print("\n🔴 문제:"); [print("  -",p) for p in problems]
        sys.exit(1 if gate else 0)
    print("\n✅ 결손·세대차 없음")

main()
