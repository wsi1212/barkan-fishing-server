# 통발(trap) 권위 소스 지도

## 메커니즘
- `JAVA/trap/TrapManager.java` — 설치/회수/틱(30초 주기)/내구도/물고기 생성(`generateFish`,
  `gradeWeight`). `TRAP_LIMIT=1`(플레이어당 동시 1개).
- `JAVA/trap/TrapSpecs.java` — 지역별 스펙(`region`,`regionLabel`,`maxDur`,`waitSec`,`recipeId`,
  레시피 재료). 12개 지역 정의(스폰도시~원양어선).
- 통발전용 어종 풀: `JSON/fish.json` → `regions.<지역>.통발` (배열). **일반 낚시 "기본" 풀과는
  별도** — 다른 지역은 전부 전용 어종(중복 없음), 붉은사막만 예외였다가 2026-07-25 수정.

## ★필수 확인 — 지역 실존 여부
통발 지역이 TrapSpecs.java/fish.json에 정의돼 있다고 실제로 존재하는 게 아니다. 반드시
`JSON/regions.json`에서 `pos1`/`pos2`가 `[0,0,0]`이 아닌지, region 자체가 키에 있는지 확인할 것
(2026-07-25 기준: 12개 중 6개만 실존 — [audits/2026-07-25-trap.md](../audits/2026-07-25-trap.md) 참조).
이 원칙은 통발뿐 아니라 **다른 모든 시스템의 "지역" 참조에 동일 적용** — 페리 노선, 마을 등도
regions.json 좌표 대조 없이 "존재한다"고 가정하지 말 것.

## 계산 공식 (재사용용)
```
평균가치/캐치 = Σ(gradeWeight[g]/Σweights × 등급기본가[g]) × 품질배율(0.675, 균등10~60평균) × 마리수(1.3, 70%1/30%2)
원/h = 평균가치/캐치 × 3600 / waitSec
```
gradeWeight = {E:100,D:80,C:55,B:32,A:16,S:8,M:4,L:2,G:1} (`TrapManager.gradeWeight`) — ★정상
낚시 PRD 확률과 무관한 별도 체계. 풀이 1~2종으로 좁으면 이 가중치가 등급 분포를 크게 왜곡한다
(예: 2종 풀에서 M등급이 포함되면 weight 4/(16+4)=20% 확률로 나옴 — 정상 PRD의 0.0035%와 비교 불가).

## 파일 위치
- 지역 실존 확인: `JSON/regions.json`
- 통발전용 어종/등급: `JSON/fish.json` regions.*.통발
- 등급 기본가: `JAVA/economy/FishItem.java` fishPrice() (낚시 데이터소스와 공유)
