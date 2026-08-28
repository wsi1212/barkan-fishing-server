#!/usr/bin/env python3
"""ModelEngine/BetterModel이 <b>구워낸</b> 리소스팩 모델(본별 vanilla JSON)을 우리 렌더러가
읽는 .bbmodel 형태로 되돌린다. <b>레퍼런스를 눈으로 보기 위한 도구</b>다.

왜 필요한가
  잘 만든 남의 모델을 숫자로만 재면(reference-study.md) "회전 30%"까지는 알아도
  <b>그게 어떻게 보이는지</b>는 모른다. 소스 .bbmodel은 못 구하지만, 리소스팩에 구워진
  본별 JSON엔 기하가 그대로 남아 있으므로 되살려 렌더할 수 있다.

★이건 관찰용이지 <b>출력 베이스가 아니다.</b> 남의 모델을 복사·리컬러해서 쓰는 건
  스킬 하드룰 위반이다(레퍼런스는 스타일 표본, 출력 베이스가 아니다).

포맷 차이 처리
  · vanilla rotation {angle, axis, origin} → bbmodel rotation [x,y,z] + origin
  · faces.texture "#1" → 텍스처 인덱스 0
  · UV는 vanilla가 0~16 정규화. 실제 텍스처가 128px면 스케일이 필요하므로
    resolution을 16x16으로 선언해 렌더러가 tex/16을 곱하게 둔다.
  · 본 계층은 남아 있지 않다(파일명뿐) → 전부 루트 자식으로 평평하게 놓는다.
    ★그래서 이 렌더는 <b>rest pose 형상</b>만 맞고, 본 회전이 걸린 모델은 다르게 보인다.
"""
import glob
import json
import os
import sys
import base64
import uuid as _uuid


def conv(dirpath, texroot):
    els, groups, outliner = [], [], []
    texfile = None
    for f in sorted(glob.glob(os.path.join(dirpath, '*.json'))):
        bone = os.path.basename(f)[:-5]
        d = json.load(open(f))
        for v in (d.get('textures') or {}).values():
            if isinstance(v, str) and ':' in v:
                texfile = os.path.join(texroot, v.split(':', 1)[1] + '.png')
        kids = []
        for e in d.get('elements', []):
            eu = str(_uuid.uuid4())
            rot = e.get('rotation')
            r3, org = [0, 0, 0], e.get('from')
            if isinstance(rot, dict):
                ax = {'x': 0, 'y': 1, 'z': 2}.get(rot.get('axis', 'y'), 1)
                r3 = [0, 0, 0]
                r3[ax] = float(rot.get('angle', 0) or 0)
                org = rot.get('origin', org)
            faces = {}
            for fn, fv in (e.get('faces') or {}).items():
                if 'uv' in fv:
                    faces[fn] = {'uv': fv['uv'], 'texture': 0}
            els.append({'name': bone, 'from': e['from'], 'to': e['to'], 'origin': org,
                        'rotation': r3, 'faces': faces, 'type': 'cube', 'uuid': eu,
                        'box_uv': False})
            kids.append(eu)
        if kids:
            gu = str(_uuid.uuid4())
            groups.append({'uuid': gu, 'name': bone, 'origin': [0, 0, 0],
                           'rotation': [0, 0, 0], 'children': kids})
            outliner.append({'uuid': gu, 'children': kids})
    tex = {'name': 'ref.png', 'uuid': str(_uuid.uuid4()), 'source': ''}
    if texfile and os.path.exists(texfile):
        tex['source'] = 'data:image/png;base64,' + base64.b64encode(
            open(texfile, 'rb').read()).decode()
    return {'meta': {'format_version': '4.5', 'model_format': 'free'},
            'name': os.path.basename(dirpath.rstrip('/')),
            'resolution': {'width': 16, 'height': 16},
            'elements': els, 'groups': groups, 'outliner': outliner,
            'textures': [tex], 'animations': []}


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    m = conv(sys.argv[1], sys.argv[2])
    json.dump(m, open(sys.argv[3], 'w'))
    print('%s  큐브 %d · 본 %d' % (sys.argv[3], len(m['elements']), len(m['groups'])))
