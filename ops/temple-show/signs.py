"""플롯마다 안내 표지판 + 씨렌턴 기둥 명령을 뽑는다 (sg_pre.txt / sg_post.txt).

★이름표를 text_display 로 하면 안 된다 — NpcDialogueManager.sweepOrphanBubbles 가
EntitiesLoad 마다 «탈것 없는 persistent TextDisplay» 를 월드 불문 전부 지운다.
소환 직후엔 멀쩡히 보이다가 청크가 한 번 언로드되면 사라진다. 그래서 블록엔티티(표지판)로 간다.
"""
import json, sys
plots = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "plots.json"))
def esc(s): return s.replace("\\", "\\\\").replace('"', '\\"')
def wrap(s, n=15):
    out, cur = [], ""
    for w in s.replace("/", "/ ").split():
        if len(cur) + len(w) + 1 <= n: cur = (cur + " " + w).strip()
        else: out.append(cur); cur = w
    if cur: out.append(cur)
    return (out + ["", ""])[:2]

pre, cmd = [], []
for p in plots:
    x, z, y = p["cx"], p["z"] - 2, p["y"]
    pre.append(f'execute in minecraft:temple_show run forceload add {x-8} {z-8} {x+8} {z+8}')
    l3, l4 = wrap(p["src"])
    msgs = ('[{text:"%s",color:"gold"},{text:"%s",color:"aqua"},'
            '{text:"%s",color:"gray"},{text:"%s",color:"gray"}]'
            % (esc(p["id"]), esc(p["ko"]), esc(l3), esc(l4)))
    txt = f'{{has_glowing_text:1b,messages:{msgs}}}'
    cmd.append(f'execute in minecraft:temple_show run fill {x} {y} {z} {x} {y+1} {z} minecraft:dark_prismarine')
    cmd.append(f'execute in minecraft:temple_show run setblock {x} {y+2} {z} '
               f'minecraft:dark_oak_sign[rotation=0]{{is_waxed:1b,front_text:{txt},back_text:{txt}}} replace')
    for dx in (-2, 2):
        cmd.append(f'execute in minecraft:temple_show run fill {x+dx} {y} {z} {x+dx} {y+3} {z} minecraft:sea_lantern')
open("sg_pre.txt", "w").write("\n".join(pre) + "\n")
open("sg_post.txt", "w").write("\n".join(cmd) + "\nsave-all flush\n")
print(f"sg_pre.txt {len(pre)}줄 / sg_post.txt {len(cmd)+1}줄")
print("실행: pre 를 먼저 다 돌리고 ★8초 쉬었다가★ post. 청크 로드는 비동기라 바로 쏘면 조용히 유실된다.")
