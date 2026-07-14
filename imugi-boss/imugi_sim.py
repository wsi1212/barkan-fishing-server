#!/usr/bin/env python3
"""이무기 애니메이션 오프라인 시뮬레이터 — ImugiBoss.java 수학 1:1 포팅.

리그+모델 박스를 읽어 유영/잠수를 시뮬레이션하고:
  - 탑다운 필름스트립 PNG (프레임 그리드)
  - 마디 겹침 수치(인접 침투 깊이, 비인접 충돌 셀 수)
를 출력한다. 인게임 확인 없이 모션 품질을 자가 검토·튜닝하는 용도.
사용: python3 imugi_sim.py [모드=swim|dive] [반경] [프레임수]
"""
import json, math, os, sys
from collections import deque
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Circle as MplCircle

SCRATCH = os.path.dirname(os.path.abspath(__file__))
RP_MODELS = os.path.expanduser("~/development/barkan-resourcepack/assets/barkan/models/imugi_s")

# ---- ImugiBoss.java 상수 (동기 필수!) ----
SPEED = 5.4
UPDATE_TICKS = 2
STEP = SPEED * UPDATE_TICKS / 20.0
BOB_AMP = 0.9
WIGGLE_AMP = 1.1
SWIM_SECONDS = 12.0
DIVE_DEPTH = 4.5

class Sim:
    def __init__(self, rig_path, center, radius, mode="swim", head_rear_pivot=0.0):
        rig = json.load(open(rig_path))
        self.mult = rig.get("render_scale_multiplier", 1.0)
        self.segs = sorted(rig["segments"], key=lambda s: s["seg"])
        self.center = np.array(center, float)
        self.radius = radius
        self.mode = mode
        # 체인 거리 (머리=마지막). head_rear_pivot>0이면 머리 pivot을 뒤(목)로 그만큼 이동한 효과
        n = len(self.segs)
        self.hrp = head_rear_pivot
        self.chain = [0.0] * n
        for i in range(n - 2, -1, -1):
            a, b = np.array(self.segs[i]["pivot"]), np.array(self.segs[i+1]["pivot"])
            g = float(np.linalg.norm(a - b))
            if i == n - 2: g = max(0.5, g - head_rear_pivot)
            self.chain[i] = self.chain[i+1] + g
        # 모델 박스 (모델좌표 → (c/16-0.5)*k 로컬옵셋, 렌더배율 포함)
        self.boxes = []
        for s in self.segs:
            m = json.load(open(os.path.join(RP_MODELS, f"seg_{s['seg']:02d}.json")))
            k_eff = s["scale"] * self.mult  # f=1 가정(스팬≤32 bake)
            zoff = self.hrp if s is self.segs[-1] else 0.0  # 리어피벗: 머리 콘텐츠를 +z로
            bs = []
            for e in m["elements"]:
                fr = [(v/16 - 0.5) * k_eff for v in e["from"]]; fr[2] += zoff
                to = [(v/16 - 0.5) * k_eff for v in e["to"]]; to[2] += zoff
                bs.append((np.array(fr), np.array(to)))
            self.boxes.append(bs)
        # 상태
        self.history = deque()
        self.theta = 0.0
        self.bob = 0.0; self.wig = 0.0
        self.swim_t = 0.0
        self.dive_path = None; self.dive_prog = 0.0
        # 원더 경로 상태
        self.w_pos = self.center + np.array([radius * 0.5, -0.4, 0.0])
        self.w_head = math.pi / 2
        self.w_n = 0
        self._preload()

    # ---- ImugiBoss 포팅 ----
    def circle_point(self, th, bob, wig):
        r = self.radius + wig
        return np.array([self.center[0] + math.cos(th) * r,
                         self.center[1] - 0.4 + bob * 0.5,
                         self.center[2] + math.sin(th) * r])

    def _preload(self):
        total = self.chain[0] + 6
        n = int(math.ceil(total / STEP)) + 4
        if self.mode in ("wander", "wdive"):  # 시작 방향 뒤로 일직선
            dirv = np.array([math.sin(self.w_head), 0, math.cos(self.w_head)])
            for i in range(n, -1, -1):
                self.history.append(self.w_pos - dirv * (i * STEP))
        else:
            for i in range(n, -1, -1):
                self.history.append(self.circle_point(self.theta - i * STEP / self.radius, 0, 0))

    def _tangent_circle(self, th):
        return np.array([-math.sin(th), 0, math.cos(th)])

    def _chaikin(self, pts):
        out = [pts[0]]
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i+1]
            out.append(a * 0.75 + b * 0.25)
            out.append(a * 0.25 + b * 0.75)
        out.append(pts[-1])
        return out

    def _build_dive(self):
        import random
        # 전방 포물선 잠수(돌고래 아크): 진행방향 ±40° 앞 16~24블록 지점에서 부상 — 몸이 같은 경로를 따라와 자기충돌 없음
        p0 = self.w_pos.copy()
        ang = self.w_head + math.radians(random.uniform(-30, 30))
        dist = random.uniform(26, 38)
        exitp = p0 + np.array([math.sin(ang), 0, math.cos(ang)]) * dist
        off = exitp - self.center; off[1] = 0
        d = float(np.linalg.norm(off))
        lim = self.radius - 3.0
        if d > lim:  # 호수 안으로 클램프
            exitp = self.center + off / d * lim
        exitp[1] = self.center[1] - 0.4
        chord = exitp - p0; chord[1] = 0
        cn = float(np.linalg.norm(chord)); chord = chord / max(cn, 1e-6)
        exit_head = math.atan2(chord[0], chord[2])
        g1 = p0 + chord * (cn * 0.12); g1[1] = self.center[1] - 1.6      # 완만 진입
        deep1 = p0 + chord * (cn * 0.32); deep1[1] = self.center[1] - DIVE_DEPTH
        mid = p0 + chord * (cn * 0.5); mid[1] = self.center[1] - DIVE_DEPTH - 0.5
        deep2 = p0 + chord * (cn * 0.68); deep2[1] = self.center[1] - DIVE_DEPTH
        g2 = p0 + chord * (cn * 0.88); g2[1] = self.center[1] - 1.6      # 완만 부상
        pts = [p0, g1, deep1, mid, deep2, g2, exitp.copy()]
        for _ in range(2): pts = self._chaikin(pts)
        self.dive_path = pts; self.dive_prog = 0.0
        self.w_pos = exitp.copy(); self.w_head = exit_head

    def _advance_dive(self):
        self.dive_prog += STEP
        acc = 0.0
        for i in range(len(self.dive_path) - 1):
            a, b = self.dive_path[i], self.dive_path[i+1]
            ln = float(np.linalg.norm(b - a))
            if acc + ln >= self.dive_prog and ln > 1e-9:
                t = (self.dive_prog - acc) / ln
                return a + (b - a) * t
            acc += ln
        self.dive_path = None
        return self.w_pos.copy()

    def wander_step(self):
        self.w_n += 1
        # 부드러운 곡률 변주 (최소회전반경 ~9 보장) + 경계 조향 + 자기회피
        kappa = (math.sin(self.w_n * 0.055) * 0.07 + math.sin(self.w_n * 0.021 + 1.7) * 0.045)
        dirv = np.array([math.sin(self.w_head), 0, math.cos(self.w_head)])
        look = self.w_pos + dirv * 9.0
        off = look - self.center; off[1] = 0
        d = float(np.linalg.norm(off))
        limit = self.radius - 2.0
        if d > limit:  # 경계 밖을 보면 중심 쪽으로 조향
            to_c = math.atan2(-off[0], -off[2])
            diff = (to_c - self.w_head + math.pi) % (2 * math.pi) - math.pi
            kappa += max(-0.11, min(0.11, diff * 0.35)) * min(1.5, (d - limit))
        # 자기회피: 전방 주시점이 몸(히스토리, 목 부근 제외)에 가까우면 반대쪽으로
        hs = list(self.history)
        neck_skip = int(10 / STEP)  # 머리 뒤 10블록은 무시
        AVOID = 5.5
        for s in hs[:-neck_skip][::4] if len(hs) > neck_skip else []:
            rel = s - self.w_pos; rel[1] = 0
            ahead = float(rel @ dirv)
            if ahead < 1.0: continue  # 뒤쪽은 무시
            la = self.w_pos + dirv * min(ahead, 9.0)
            dd = float(np.linalg.norm((s - la) * np.array([1, 0, 1])))
            if dd < AVOID:
                side = dirv[0] * rel[2] - dirv[2] * rel[0]  # >0: 오른쪽에 장애물
                kappa += (0.10 if side > 0 else -0.10) * (AVOID - dd) / AVOID
        self.w_head += max(-0.115, min(0.115, kappa))
        self.bob += 0.22
        step = np.array([math.sin(self.w_head), 0, math.cos(self.w_head)]) * STEP
        self.w_pos = self.w_pos + step
        self.w_pos[1] = self.center[1] - 0.4 + BOB_AMP * 0.5 * math.sin(self.bob)
        return self.w_pos.copy()

    def tick(self):
        if self.dive_path is not None:
            nxt = self._advance_dive()
        elif self.mode in ("wander", "wdive"):
            nxt = self.wander_step()
            if self.mode == "wdive":
                self.swim_t += UPDATE_TICKS / 20.0
                if self.swim_t >= SWIM_SECONDS:
                    self.swim_t = 0; self._build_dive()
        else:
            self.theta += STEP / self.radius
            self.bob += 0.22; self.wig += 0.33
            nxt = self.circle_point(self.theta, BOB_AMP * math.sin(self.bob),
                                    WIGGLE_AMP * math.sin(self.wig))
            if self.mode == "dive":
                self.swim_t += UPDATE_TICKS / 20.0
                if self.swim_t >= SWIM_SECONDS:
                    self.swim_t = 0; self._build_dive()
        self.history.append(nxt)
        cap = int(math.ceil((self.chain[0] + 10) / STEP)) + 8
        while len(self.history) > cap: self.history.popleft()

    def pos_at(self, dist):
        acc = 0.0
        hs = list(self.history)
        cur = hs[-1]
        for i in range(len(hs) - 2, -1, -1):
            prev = hs[i]
            ln = float(np.linalg.norm(cur - prev))
            if acc + ln >= dist and ln > 1e-9:
                t = (dist - acc) / ln
                return cur + (prev - cur) * t
            acc += ln; cur = prev
        return cur.copy()

    def sample(self, dist):
        pos = self.pos_at(dist)
        tan = self.pos_at(max(0, dist - 0.9)) - self.pos_at(dist + 0.9)
        n = float(np.linalg.norm(tan))
        return pos, (tan / n if n > 1e-9 else np.array([0, 0, 1.0]))

    def frame(self):
        """마디별 (pos, R행렬) — R = rotYXZ(yaw, pitch, 0), 넷 변환(플립 상쇄) 기준."""
        out = []
        for i in range(len(self.segs)):
            pos, tan = self.sample(self.chain[i])
            yaw = math.atan2(tan[0], tan[2])
            pitch = -math.asin(max(-1, min(1, tan[1])))
            cy, sy = math.cos(yaw), math.sin(yaw)
            cp, sp = math.cos(pitch), math.sin(pitch)
            Ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
            Rx = np.array([[1,0,0],[0,cp,-sp],[0,sp,cp]])
            out.append((pos, Ry @ Rx))
        return out

    # ---- 겹침 수치화: 마디 박스를 0.5해상도 복셀로 → 침투 측정 ----
    def overlap_stats(self, frame):
        occ = {}
        for i, (pos, R) in enumerate(frame):
            for fr, to in self.boxes[i]:
                # 8꼭짓점 회전 → AABB로 근사(보수적) 후 복셀화
                corners = np.array([[fr[0],fr[1],fr[2]],[to[0],fr[1],fr[2]],[fr[0],to[1],fr[2]],[fr[0],fr[1],to[2]],
                                    [to[0],to[1],fr[2]],[to[0],fr[1],to[2]],[fr[0],to[1],to[2]],[to[0],to[1],to[2]]])
                w = (R @ corners.T).T + pos
                lo, hi = w.min(0), w.max(0)
                for x in np.arange(math.floor(lo[0]*2)/2, hi[0], 0.5):
                    for y in np.arange(math.floor(lo[1]*2)/2, hi[1], 0.5):
                        for z in np.arange(math.floor(lo[2]*2)/2, hi[2], 0.5):
                            occ.setdefault((x, y, z), set()).add(i)
        adj = sum(1 for s in occ.values() if any(abs(a-b) == 1 for a in s for b in s if a < b))
        far = sum(1 for s in occ.values() if any(abs(a-b) > 1 for a in s for b in s if a < b))
        return adj, far  # 인접겹침셀, 비인접겹침셀 (0.125블록³ 단위)

    # ---- 탑다운 렌더 ----
    def draw_top(self, ax, frame, title=""):
        cmap = plt.cm.viridis(np.linspace(0.1, 0.95, len(self.segs)))
        ax.add_patch(MplCircle((self.center[0], self.center[2]), self.radius + 3,
                               fill=True, color='#b9dcf2', zorder=0))
        for i, (pos, R) in enumerate(frame):
            for fr, to in self.boxes[i]:
                pts = np.array([[fr[0],0,fr[2]],[to[0],0,fr[2]],[to[0],0,to[2]],[fr[0],0,to[2]]])
                pts[:,1] = (fr[1]+to[1])/2
                w = (R @ pts.T).T + pos
                ax.add_patch(MplPoly(w[:, [0, 2]], closed=True, facecolor=cmap[i],
                                     edgecolor='k', linewidth=0.2, alpha=0.75))
        ax.set_xlim(self.center[0]-self.radius-9, self.center[0]+self.radius+9)
        ax.set_ylim(self.center[2]-self.radius-9, self.center[2]+self.radius+9)
        ax.set_aspect('equal'); ax.set_title(title, fontsize=7); ax.axis('off')

    def draw_side(self, ax, frame, title=""):
        cmap = plt.cm.viridis(np.linspace(0.1, 0.95, len(self.segs)))
        ax.axhspan(self.center[1]-8.0, self.center[1]+0.1, color='#b9dcf2', zorder=0)   # 물(신규 호수 수심 ~8)
        ax.axhspan(self.center[1]-12, self.center[1]-8.0, color='#c9b18a', zorder=0)    # 바닥
        for i, (pos, R) in enumerate(frame):
            for fr, to in self.boxes[i]:
                pts = np.array([[fr[0],fr[1],fr[2]],[to[0],fr[1],fr[2]],[to[0],to[1],to[2]],[fr[0],to[1],to[2]]])
                w = (R @ pts.T).T + pos
                ax.add_patch(MplPoly(w[:, [2, 1]], closed=True, facecolor=cmap[i],
                                     edgecolor='k', linewidth=0.2, alpha=0.75))
        ax.set_xlim(self.center[2]-self.radius-9, self.center[2]+self.radius+9)
        ax.set_ylim(self.center[1]-9, self.center[1]+7)
        ax.set_aspect('equal'); ax.set_title(title, fontsize=7); ax.axis('off')


def run(mode="swim", radius=11.0, frames=36, out="sim_strip.png", rig="imugi_s_rig.json",
        skip_between=5, stats_every=6, head_rear_pivot=0.0):
    sim = Sim(os.path.join(SCRATCH, rig), (150, -60, -100), radius, mode, head_rear_pivot)
    if mode == "wdive": sim.swim_t = SWIM_SECONDS - 2.0  # 잠수를 2초 뒤 바로 트리거
    side = mode == "wdive"
    cols = 6
    rows = math.ceil(frames / 6) * (2 if side else 1)
    fig, axes = plt.subplots(rows, cols, figsize=(cols*2.6, rows*2.6))
    axes = np.atleast_2d(axes)
    stats = []
    for f in range(frames):
        for _ in range(skip_between): sim.tick()
        fr = sim.frame()
        t = f * skip_between * UPDATE_TICKS / 20.0
        adjc, farc = sim.overlap_stats(fr) if f % stats_every == 0 else (None, None)
        if adjc is not None: stats.append((round(t,1), adjc, farc))
        r0 = (f // cols) * (2 if side else 1)
        sim.draw_top(axes[r0][f % cols], fr, f"t={t:.1f}s" + (f" adj{adjc}/far{farc}" if adjc is not None else ""))
        if side: sim.draw_side(axes[r0+1][f % cols], fr, "side")
    for rr in range(rows):
        for cc in range(cols):
            if not axes[rr][cc].has_data(): axes[rr][cc].axis('off')
    plt.tight_layout(); plt.savefig(os.path.join(SCRATCH, out), dpi=85); plt.close()
    print("saved", out)
    print("overlap(t, 인접셀, 비인접셀):", stats)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "swim"
    radius = float(sys.argv[2]) if len(sys.argv) > 2 else 11.0
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 36
    hrp = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0  # 리그가 리어피벗(-98)로 구워지면 0 사용
    out = sys.argv[5] if len(sys.argv) > 5 else "sim_strip.png"
    run(mode, radius, frames, out=out, head_rear_pivot=hrp)
