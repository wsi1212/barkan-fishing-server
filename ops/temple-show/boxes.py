"""월드형 소스의 크롭 박스 산출 → boxes.json"""
import json
def box(cx, cz, half, y0=0, y1=250):
    return [cx-half, y0, cz-half, cx+half-1, y1, cz+half-1]
B = {
 "10": [-184, 4, 56, -89, 111, 167],        # 탐지된 성채 클러스터 + 여백
 "11": box(199, 320, 112, 4, 180),          # 사암/석영 궁전 클러스터(스폰 주변)
 "16": box(853, 795, 128, 4, 200),          # 제작자 마지막 위치 기준
 "17": box(552, 973, 128, 40, 240),
 "18": [-184, 0, 152, 183, 185, 439],       # 탐지 클러스터 + 여백
 "19": box(682, 724, 128, 4, 240),
}
json.dump(B, open("boxes.json","w"), indent=1)
print(json.dumps(B))
