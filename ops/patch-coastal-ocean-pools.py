#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""바르칸_연안 / 대양 낚시 풀을 «선언된 어종 목록»에서 다시 뽑는다 (2026-09-08 유저 지시).

★손편집 금지 — 목록을 고치고 이 스크립트를 다시 돌린다.

버킷 규칙은 대양이 이미 쓰고 있던 관례를 그대로 따른다:
    def.time == 전체 → 기본
    def.time == 낮   → 낮맑음 / 낮비   (def.weather 로 한쪽만 걸릴 수 있음)
    def.time == 밤   → 밤맑음 / 밤비
    def.weather == 맑음 → 맑음 버킷만 · 비/뇌우 → 비 버킷만 · 전체 → 양쪽
(FishingListener 는 밤에 낮버킷을 25% 로만 섞고, 낮엔 밤버킷을 아예 안 넣는다.)

보존하는 것:
  · 통발 버킷 — 낚싯대 풀이 아니다(ROD_SUBLISTS 밖). 지우면 그 지역 통발이 기본 풀로 폴백한다.
  · 퀘스트 게이트 어종(def.quest) — 해당 퀘스트 진행 중인 사람에게만 풀에 들어가고 도감에도 안 뜬다.
    대양의 교단의해도(심해09)·교단의표식(심해15)은 대양이 유일한 출현지라 지우면 메인 스토리가 영구 진행불가.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FISH_JSON = os.path.join(ROOT, "ops", "blockship-data", "fish.json")
ROD_SUBLISTS = ["기본", "낮맑음", "낮비", "밤맑음", "밤비"]

# ── 선언 목록 (유저 지시 원문 순서 = 등급 오름차순) ────────────────────────────
POOLS = {
    "바르칸_연안": {
        "E": ["멸치", "정어리", "미꾸라지", "피라미", "불가사리", "바다나리", "쫄복", "바다황어"],
        "D": ["쥐치", "전갱이", "보구치", "오징어", "고등어", "붕어", "우럭", "곰치", "대구",
              "청어", "잿방어", "부시리", "삼치"],
        # 지시 원문의 «꽁치»는 fish.json 에 없는 이름이라 «학꽁치» 로 확정(2026-09-08 유저 결정).
        "C": ["학꽁치", "도다리", "볼락", "광어", "농어", "문어", "갈치", "쭈꾸미", "참돔", "가자미"],
        "B": ["갑오징어", "벵에돔", "숭어", "홍어", "혹돔", "옥돔", "만새기", "블루탱"],
        "A": ["나뭇잎해룡", "참복", "해마", "돌돔", "대왕대게", "다금바리", "민어"],
        "S": ["장수거북", "돗돔", "백상아리", "노틸러스"],
        "M": ["메가마우스상어", "반딧불이오징어"],
    },
    "대양": {
        "E": ["꼬치고기", "달고기", "쥐노래미", "바다황어", "노래미", "참놀래기", "쑤기미", "쏨뱅이",
              "말쥐치", "쏠배감펭", "독가시치", "양태", "성대", "황놀래기", "자리돔", "쫄복", "멸치", "정어리"],
        "D": ["곰치", "부시리", "잿방어", "아귀", "청대치", "대구", "바다숭어", "삼치",
              "점농어", "가숭어", "빨판상어", "명태", "홍서대", "우럭", "고등어", "청어", "날치", "전갱이"],
        "C": ["미흑점상어", "괭이상어", "곱상어", "신락상어", "줄삼치", "방어", "노랑가오리", "별상어",
              "갈치", "바다농어", "광어", "참돔", "쥐치복", "감성돔", "볼락", "가자미", "문절망둑", "학꽁치"],
        "B": ["가래상어", "무태상어", "매가오리", "흑기흉상어", "블랙팁샤크", "레오파드상어", "산호상어", "전기가오리",
              "만새기", "혹돔", "가다랑어", "홍어", "벵에돔", "옥돔", "블루탱", "흰동가리", "숭어", "만다린피시"],
        "A": ["귀상어", "뱀상어", "청상아리", "황소상어", "환도상어", "참다랑어", "붕장어", "갯장어", "붉평치", "자바리",
              "다금바리", "민어", "능성어", "바라쿠다", "돌돔", "참복", "해마", "나뭇잎해룡"],
        "S": ["톱상어", "톱가오리", "만타가오리", "대왕쥐가오리", "돛새치", "백상아리", "개복치",
              "청새치", "나폴레옹피쉬", "돗돔", "해룡", "배럴아이", "흑진주 참치", "장수거북"],
        "M": ["메가마우스상어", "뇌전가오리", "밍크고래", "참고래", "풍선장어"],
        "L": ["향유고래", "고래상어", "혹등고래", "귀신고래"],
        "G": ["산갈치"],
    },
}

# ── 등급 승격 (2026-09-08 유저 결정) ──────────────────────────────────────────
# 산갈치는 지시 목록에서 G로 적혀 있었고 fish.json 은 M이었다. G 승격의 대가는 알고 간다:
# 레벨 게이트 Lv.30 → Lv.60, base 확률 0.0105% → 0.0000175% (평균 122캐스트 → 3002캐스트).
GRADE_OVERRIDES = {"산갈치": "G"}

# ── 대양에서 빠지는 어종의 새 서식지 (2026-09-08 유저 결정) ────────────────────
# 대양 목록에서 빠진 15종 중 이 6종은 «대양이 유일한 출현지»였다 → 그대로 지우면 서버
# 어디서도 안 잡히고 전체 도감에 영구 미획득으로 남는다. 성격이 가장 가까운 심해 지역인
# 원양(Lv.50 제한)으로 옮긴다. 나머지 9종은 원양·부두에 이미 살아 있어 손대지 않는다.
RELOCATE = {
    "원양": ["골리앗그루퍼", "대왕오징어", "흑새치", "황금 방어", "모래뱀상어", "무늬오징어"],
}


def buckets_for(defn):
    t, w = defn.get("time", "전체"), defn.get("weather", "전체")
    if t == "전체":
        return ["기본"]
    prefix = "낮" if t == "낮" else "밤"
    if w == "맑음":
        return [prefix + "맑음"]
    if w in ("비", "뇌우"):
        return [prefix + "비"]
    return [prefix + "맑음", prefix + "비"]


def main():
    with open(FISH_JSON, encoding="utf-8") as fp:
        data = json.load(fp)
    F, R, ENV = data["fish"], data["regions"], data["environment"]
    env_all = {n for lst in ENV.values() for n in lst}

    promoted = []
    for name, grade in GRADE_OVERRIDES.items():
        if name not in F:
            print(f"✗ 등급 승격 대상 '{name}' 이 fish.json 에 없다", file=sys.stderr)
            return 1
        if F[name].get("grade") != grade:
            promoted.append((name, F[name].get("grade"), grade))
            F[name]["grade"] = grade

    relocated = []
    for region, names in RELOCATE.items():
        if region not in R:
            print(f"✗ 재배치 대상 지역 '{region}' 이 fish.json 에 없다", file=sys.stderr)
            return 1
        here = {n for lst in R[region].values() for n in lst}
        for n in names:
            if n not in F:
                print(f"✗ 재배치 대상 어종 '{n}' 이 fish.json 에 없다", file=sys.stderr)
                return 1
            if n in here:
                continue
            for b in buckets_for(F[n]):
                R[region].setdefault(b, []).append(n)
            relocated.append((region, n, F[n]["grade"]))

    errors, warns, report = [], [], []
    for region, by_grade in POOLS.items():
        wanted = [n for names in by_grade.values() for n in names]
        dup = [n for n in set(wanted) if wanted.count(n) > 1]
        if dup:
            errors.append(f"{region}: 목록 중복 {dup}")
        for grade, names in by_grade.items():
            for n in names:
                if n not in F:
                    errors.append(f"{region}: 없는 어종 '{n}'")
                elif F[n].get("grade") != grade:
                    # 등급은 fish.json def 가 권위 — 풀 배정과 무관하므로 경고만 낸다.
                    warns.append(f"{region}: '{n}' 등급 표기 차이 (목록 {grade} / fish.json {F[n]['grade']})")
        if errors:
            continue

        old = R.get(region, {})
        old_union = {n for b in ROD_SUBLISTS for n in old.get(b, [])}
        # 퀘스트 게이트 어종은 목록에 없어도 보존 (진행 중인 사람에게만 보이는 숨은 항목)
        keep_quest = sorted(n for n in old_union
                            if F.get(n, {}).get("quest") and n not in wanted)
        # 전역 환경 풀이 이미 소유한 어종은 지역 버킷에 넣지 않는다
        skipped_env = [n for n in wanted if n in env_all]

        new = {}
        for n in wanted:
            if n in env_all:
                continue
            for b in buckets_for(F[n]):
                new.setdefault(b, []).append(n)
        for n in keep_quest:
            for b in buckets_for(F[n]):
                new.setdefault(b, []).append(n)

        out = {}
        for b in ROD_SUBLISTS:
            if new.get(b):
                out[b] = new[b]
        if old.get("통발"):                       # 통발은 손대지 않는다
            out["통발"] = old["통발"]
        for b, lst in old.items():                # 낯선 버킷(이벤트 등)도 보존
            if b not in ROD_SUBLISTS and b != "통발":
                out[b] = lst
        R[region] = out

        new_union = {n for b in ROD_SUBLISTS for n in out.get(b, [])}
        report.append((region, sorted(old_union - new_union), sorted(new_union - old_union),
                       keep_quest, skipped_env,
                       {b: len(out.get(b, [])) for b in ROD_SUBLISTS + ["통발"] if out.get(b)}))

    if errors:
        print("✗ 중단 — 목록 오류:", file=sys.stderr)
        for e in errors:
            print("   " + e, file=sys.stderr)
        return 1

    if "--dry-run" not in sys.argv:
        with open(FISH_JSON, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
            fp.write("\n")

    for w in warns:
        print("⚠ " + w)
    for name, old_g, new_g in promoted:
        print(f"↑ 등급 승격: {name} {old_g} → {new_g}")
    for region, n, g in relocated:
        print(f"→ 재배치: {n}({g}) → {region}/{'·'.join(buckets_for(F[n]))}")
    for region, removed, added, quest, env, counts in report:
        print(f"\n=== {region} ===")
        print("  버킷:", ", ".join(f"{b} {c}" for b, c in counts.items()))
        print(f"  삭제 {len(removed)}: {removed or '없음'}")
        print(f"  추가 {len(added)}: {added or '없음'}")
        if quest:
            print(f"  ※ 퀘스트 게이트라 보존: {quest}")
        if env:
            print(f"  ※ 전역 환경 풀이 이미 소유(지역 버킷 생략): {env}")
    print("\n" + ("[dry-run] 파일 미변경" if "--dry-run" in sys.argv else "✓ fish.json 갱신"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
