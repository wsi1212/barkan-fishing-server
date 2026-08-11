#!/usr/bin/env python3
"""In-game ground-truth verification: summon item_display entities showing your
models on the dev server, so a screenshot shows what the GAME actually renders
(lighting, background, angles) — not an offline approximation.

Spawns each model on a small grass platform in the sky (y=200) via RCON console
commands only — no player needed. Then take a screenshot (mc_screenshot MCP,
which renders dev) aimed at the plot, Read it, critique, repaint, repeat.

Usage:
  python ingame_verify.py place barkan:forage_z_mushred barkan:forage_z_fruit ...
  python ingame_verify.py clean
Prints the camera position/target to aim the screenshot at.
Plot: overworld, centered near (0, 200, 0), items 2 blocks apart along +x.
"""
import socket, struct, sys, time

HOST, PORT, PW = "127.0.0.1", 25575, "devtest2026"
# ★검증장은 castle_show(공허 전시월드) — 본월드 지역시스템(강/깊은물/날씨)과 충돌 방지 (2026-07-17 강 수몰 사고 후 이전)
DIM = "minecraft:castle_show"
BASE_X, Y, Z = 0, 200, 1000
TAG = "pxverify"

def rcon(cmds):
    s = socket.create_connection((HOST, PORT), timeout=6)
    def pk(rid, typ, body):
        b = body.encode() + b"\x00\x00"
        return struct.pack("<iii", len(b)+8, rid, typ) + b
    def rd():
        ln = struct.unpack("<i", s.recv(4))[0]
        data = b""
        while len(data) < ln: data += s.recv(ln - len(data))
        return data[8:-2].decode(errors="replace")
    s.sendall(pk(1, 3, PW)); rd()
    outs = []
    for c in cmds:
        s.sendall(pk(2, 2, c)); time.sleep(0.15); outs.append(rd())
    s.close(); return outs

def place(models):
    cmds = [f"execute in {DIM} run forceload add {BASE_X} {Z}"]
    for i, m in enumerate(models):
        x = BASE_X + i*2
        cmds.append(f"execute in {DIM} run setblock {x} {Y-1} {Z} minecraft:grass_block")
        cmds.append(
            f'execute in {DIM} run summon minecraft:item_display {x}.5 {Y}.5 {Z}.5 '
            f'{{Tags:["{TAG}"],item_display:"fixed",transformation:{{scale:[1f,1f,1f]}},'
            f'item:{{id:"minecraft:paper",count:1,components:{{"minecraft:item_model":"{m}"}}}}}}')
    for o in rcon(cmds): print(" ", o or "(ok)")
    n = len(models)
    cx = BASE_X + (n-1)                      # grid center x
    print(f"\n[camera] pos=({cx}, {Y+2}, {Z+6}) look_at=({cx}, {Y}, {Z}) — mc_screenshot로 촬영")

def clean():
    for o in rcon([
        f"execute in {DIM} run kill @e[type=minecraft:item_display,tag={TAG}]",
        f"execute in {DIM} run fill {BASE_X-2} {Y-1} {Z-2} {BASE_X+30} {Y-1} {Z+2} minecraft:air",
        f"execute in {DIM} run forceload remove {BASE_X} {Z}"]):
        print(" ", o or "(ok)")

if __name__ == "__main__":
    if sys.argv[1] == "clean": clean()
    else: place(sys.argv[2:] if sys.argv[1] == "place" else sys.argv[1:])
