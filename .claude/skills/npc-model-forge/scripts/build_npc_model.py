#!/usr/bin/env python3
"""플레이어 리그(steve.bbmodel) + 우리 스킨 + 3D 소품 → NPC용 .bbmodel 한 장.

  build_npc_model.py <스킨.png> <출력.bbmodel> [--hat] [--basket=left|right] [--props=x.png]

왜 이 구조인가
  · 몸통·얼굴·팔다리는 <b>이미 있는 64x64 스킨이 그대로</b> 입혀진다(실측 확인).
    다시 모델링할 이유가 없다 — 새로 만들 건 스킨으로 표현 못 하는 <b>부피</b>뿐이다.
  · 소품은 텍스처 슬롯 1번(props)을 따로 쓴다. 0번은 스킨이라 빈자리가 없다.
  · 부품 정의는 parts.py에, 재질은 props_texture.py에 분리 — 스펙과 재단을 나눈 건
    skin-forge와 같은 사상이다.
"""
import base64
import copy
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts  # noqa: E402

RIG = (pathlib.Path.home() / 'Library/Application Support/feather/player-server/servers/'
       '07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/BetterModel/players/steve.bbmodel')


def datauri(path):
    return 'data:image/png;base64,' + base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def build(skin, props, hat=True, basket_side='left', rig=RIG):
    m = json.loads(pathlib.Path(rig).read_text(encoding='utf-8'))
    # 0번 = 스킨 교체
    m['textures'][0]['source'] = datauri(skin)
    m['textures'][0]['name'] = os.path.basename(skin)
    # 1번 = 소품 아틀라스 (없으면 추가)
    tex1 = copy.deepcopy(m['textures'][0])
    tex1['name'] = 'props.png'
    tex1['uuid'] = tex1.get('uuid', '') + '-props'
    tex1['source'] = datauri(props)
    m['textures'] = [m['textures'][0], tex1]

    # ★부모 본을 찾아 그 아래에 끼운다. outliner는 uuid 중첩, groups는 메타 — 둘 다 넣어야 한다.
    gby = {g['name']: g['uuid'] for g in m['groups']}

    def attach(parent_name, els, grp, outnode):
        m['elements'].extend(els)
        m['groups'].append(grp)
        pu = gby.get(parent_name)
        if pu is None:
            m['outliner'].append(outnode)
            return
        def walk(nodes):
            for n in nodes:
                if isinstance(n, dict):
                    if n.get('uuid') == pu:
                        n.setdefault('children', []).append(outnode)
                        return True
                    if walk(n.get('children', [])):
                        return True
            return False
        if not walk(m['outliner']):
            m['outliner'].append(outnode)
        # groups 쪽 부모 children에도 등록(도구 호환)
        for g in m['groups']:
            if g['uuid'] == pu:
                g.setdefault('children', []).append(grp['uuid'])

    if hat:
        attach('h_ph_head', *parts.straw_hat())
    if basket_side:
        attach('pli_left_item' if basket_side == 'left' else 'pri_right_item',
               *parts.basket(basket_side))
    return m


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = {a.split('=')[0]: (a.split('=')[1] if '=' in a else True)
            for a in sys.argv[1:] if a.startswith('--')}
    if len(args) < 2:
        print(__doc__)
        return 1
    props = opts.get('--props', '/tmp/props.png')
    m = build(args[0], props,
              hat=bool(opts.get('--hat', True)),
              basket_side=(None if opts.get('--basket') in (None, 'none')
                           else (opts.get('--basket') if isinstance(opts.get('--basket'), str)
                                 else 'left')))
    json.dump(m, open(args[1], 'w'))
    print('%s  큐브 %d · 본 %d · 텍스처 %d'
          % (args[1], len(m['elements']), len(m['groups']), len(m['textures'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
