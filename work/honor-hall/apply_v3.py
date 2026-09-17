"""Scoped, checked replacement of our own v1 build on the local dev bridge."""
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path
from collections import Counter

sys.path.insert(0,'/Users/user/development/ai-builder-plugin/tools')
from recipe_api import Api

HERE=Path(__file__).resolve().parent
BASE='http://127.0.0.1:25598'
WORLD='honor_hall'

def post(endpoint, body):
    body={'world':WORLD,**body}
    req=urllib.request.Request(BASE+endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=90) as r:
        result=json.load(r)
    if result.get('error') or result.get('ok') is False:
        raise RuntimeError(result)
    return result

def compile_recipe(file,origin):
    spec=importlib.util.spec_from_file_location(file,HERE/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    s=mod.build(Api())
    return {tuple(p[i]+origin[i] for i in range(3)):v for p,v in s.blocks.items()}

def read_live():
    result={}
    for lo in range(-58,59,25):
        hi=min(58,lo+24)
        r=post('/inspect_volume',{'x1':lo,'x2':hi,'y1':64,'y2':94,'z1':-59,'z2':81,'format':'sparse','include_air':False})
        for x,y,z,i in r['blocks']:
            result[(lo+x,64+y,-59+z)]=r['legend'][i]
    return result

def send(blocks,label):
    entries=[{'x':p[0],'y':p[1],'z':p[2],'material':v} for p,v in blocks]
    for i in range(0,len(entries),5000):
        r=post('/place_many',{'blocks':entries[i:i+5000]})
        print(label,i+len(entries[i:i+5000]),'/',len(entries),r,flush=True)

def main():
    old=compile_recipe('honor_hall.py',(-55,64,-56))
    new=compile_recipe('honor_hall_v3.py',(-96,63,-96))
    live=read_live()
    if '--verify' not in sys.argv:
        collisions=[]
        for p,v in new.items():
            actual=live.get(p,'minecraft:air')
            if p[1]>=65 and actual!='minecraft:air' and p not in old and actual!=v.split('[')[0]:
                collisions.append((p,actual))
        changed_old=[(p,live.get(p)) for p,v in old.items() if p[1]>=65 and live.get(p,'minecraft:air') not in ('minecraft:air',v.split('[')[0])]
        if collisions or changed_old:
            raise RuntimeError({'unexpected_target_blocks':collisions[:20],'changed_v1_blocks':changed_old[:20]})
        cleanup=[]
        for p,v in old.items():
            if p not in new and live.get(p)==v.split('[')[0]:
                cleanup.append((p,'grass_block' if p[1]==64 else 'air'))
        send(cleanup,'Remove obsolete v1 blocks')
        solid=sorted(((p,v) for p,v in new.items() if not v.startswith('minecraft:water')),key=lambda pv:(pv[0][1],pv[0][0],pv[0][2]))
        water=[(p,v) for p,v in new.items() if v.startswith('minecraft:water')]
        send(solid,'Install preview geometry')
        send(water,'Fill contained ponds')
        live=read_live()
    differences=[{'pos':p,'expected':v,'actual':live.get(p,'minecraft:air')} for p,v in new.items() if live.get(p,'minecraft:air')!=v.split('[')[0]]
    report={'world':WORLD,'expected_blocks':len(new),'mismatches':len(differences),'samples':differences[:40],
            'actual_palette':dict(Counter(live.get(p,'minecraft:air') for p in new))}
    (HERE/'verification_v3.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if differences: sys.exit(1)

if __name__=='__main__': main()
