"""CMU Graphics Lab ASF/AMC 파서 + FK (numpy 없음, 순수 python 3x3 행렬).

ASF(스켈레톤 정의)+AMC(모션) 포맷은 CMU mocap 데이터베이스(mocap.cs.cmu.edu)의
네이티브 포맷. 이 모듈은 파일을 읽어 프레임별 월드 포지션/로테이션을 계산하는
forward-kinematics만 제공한다. 우리 리그로의 리타게팅은 retarget.py 참고.
"""
import math
import re


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mat_vec(m, v):
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def mat_transpose(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


def rot_x(deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def rot_y(deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rot_z(deg):
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def euler_xyz(rx, ry, rz):
    """ASF 관례: R = Rx * Ry * Rz (axis/dof 값에 공통 적용)"""
    return mat_mul(mat_mul(rot_x(rx), rot_y(ry)), rot_z(rz))


def decompose_xyz(R):
    """R = Rx(rx)*Ry(ry)*Rz(rz) 가정하고 각도(도) 역산. ry가 ±90 근처면 짐벌락
    (rx/rz가 결합돼 개별 값이 요동침 — 이 경우 그 축은 쓰지 말고 raw dof 값을 직접 쓸 것)."""
    ry = math.asin(max(-1, min(1, R[0][2])))
    cb = math.cos(ry)
    if abs(cb) > 1e-6:
        rx = math.atan2(-R[1][2], R[2][2])
        rz = math.atan2(-R[0][1], R[0][0])
    else:
        rx = math.atan2(R[2][1], R[1][1])
        rz = 0.0
    return math.degrees(rx), math.degrees(ry), math.degrees(rz)


def parse_asf(path):
    text = open(path).read()
    lines = [l.rstrip() for l in text.splitlines()]
    i = 0
    bones = {}
    hierarchy = {}
    root_info = {"order": ["TX", "TY", "TZ", "RX", "RY", "RZ"], "axis": "XYZ"}

    def toks(l):
        return l.split()

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith(":root"):
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(":"):
                t = toks(lines[i].strip())
                if t and t[0] == "order":
                    root_info["order"] = t[1:]
                elif t and t[0] == "axis":
                    root_info["axis"] = t[1]
                i += 1
            continue
        if line.startswith(":bonedata"):
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(":"):
                if lines[i].strip() == "begin":
                    name = None; direction = [0, 0, 0]; length = 1.0; axis = [0, 0, 0]; dof = []
                    i += 1
                    while lines[i].strip() != "end":
                        t = toks(lines[i].strip())
                        if t[0] == "name":
                            name = t[1]
                        elif t[0] == "direction":
                            direction = [float(x) for x in t[1:4]]
                        elif t[0] == "length":
                            length = float(t[1])
                        elif t[0] == "axis":
                            axis = [float(x) for x in t[1:4]]
                        elif t[0] == "dof":
                            dof = t[1:]
                        i += 1
                    bones[name] = {"direction": direction, "length": length, "axis": axis, "dof": dof}
                i += 1
            continue
        if line.startswith(":hierarchy"):
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(":") and lines[i].strip() != "":
                if lines[i].strip() == "begin":
                    i += 1
                    while lines[i].strip() != "end":
                        t = toks(lines[i].strip())
                        if t:
                            parent = t[0]
                            for child in t[1:]:
                                hierarchy[child] = parent
                        i += 1
                i += 1
            continue
        i += 1
    return bones, hierarchy, root_info


def parse_amc(path, bones):
    frames = []
    cur = None
    for raw in open(path):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(":"):
            continue
        t = line.split()
        if len(t) == 1 and re.match(r"^\d+$", t[0]):
            if cur is not None:
                frames.append(cur)
            cur = {}
            continue
        name = t[0]
        vals = [float(x) for x in t[1:]]
        cur[name] = vals
    if cur is not None:
        frames.append(cur)
    return frames


class Skeleton:
    def __init__(self, asf_path):
        self.bones, self.parent_of, self.root_info = parse_asf(asf_path)
        for name, b in self.bones.items():
            b["C"] = euler_xyz(*b["axis"])
            b["Cinv"] = mat_transpose(b["C"])  # 순수회전이라 역행렬=전치
        self.children_of = {}
        for c, p in self.parent_of.items():
            self.children_of.setdefault(p, []).append(c)

    def local_rot(self, bone_name, frame):
        """이 본의 부모 프레임 기준 회전(=C@Rdof@Cinv). 부모/조상의 회전과 무관하게
        정의되므로(수학적으로 상쇄) 리타게팅엔 이것만 있으면 되고 전체 FK는 불필요."""
        b = self.bones[bone_name]
        dof = b["dof"]
        vals = frame.get(bone_name, [])
        angles = {"rx": 0.0, "ry": 0.0, "rz": 0.0}
        for k, axname in enumerate(dof):
            if k < len(vals):
                angles[axname.lower()] = vals[k]
        Rdof = euler_xyz(angles["rx"], angles["ry"], angles["rz"])
        return mat_mul(mat_mul(b["C"], Rdof), b["Cinv"])

    def raw_dof(self, frame, bone, idx=0, default=0.0):
        """단일 DOF 본(팔꿈치 rradius, 무릎 rtibia 등)은 decompose 하지 말고 이 raw
        채널 값을 직접 쓸 것 — decompose는 짐벌락(ry≈±90) 근처에서 rx/rz가 요동친다."""
        v = frame.get(bone, [])
        return v[idx] if idx < len(v) else default

    def fk(self, frame):
        """전체 forward-kinematics(월드 pos/rot). 시각화·검증용 — 리타게팅 자체엔 불필요."""
        world = {}
        root_vals = frame.get("root", [0, 0, 0, 0, 0, 0])
        tx, ty, tz, rx, ry, rz = root_vals
        world["root"] = ([tx, ty, tz], euler_xyz(rx, ry, rz))

        def recurse(name):
            for child in self.children_of.get(name, []):
                b = self.bones[child]
                p_pos, p_rot = world[name]
                local = self.local_rot(child, frame)
                world_rot = mat_mul(p_rot, local)
                d = b["direction"]
                world_pos = [p_pos[i] + b["length"] * mat_vec(world_rot, d)[i] for i in range(3)]
                world[child] = (world_pos, world_rot)
                recurse(child)

        recurse("root")
        return world
