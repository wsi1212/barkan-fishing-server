# 농사 권위 소스 지도

농사는 두 경로를 분리해서 본다.

1. **특수작물**: `crop/CropSpecs.java`의 고정 성장시간·수확량. 산출물은 요리 재료 전용이다.
2. **섬상점 바닐라 농사**: 런타임 `plugins/BlockShip/shop-items.json`의 `key=농사` 판매가와
   `crop/VanillaFarmListener.java`·`skill/SkillManager.java`의 실제 수확/보너스 경로. 이 경로는
   Minecraft random tick 성장이라 고정 growSec가 코드에 없으며, 시간당 수익은 반드시 성장시간
   가정을 함께 기록해야 한다.

`VanillaFarmListener`는 자연 성장으로 인정된 플레이어 파종 작물의 수확 시점에
`crop.harvest.vanilla.cycle` telemetry(`crop`, `grow_actual_s`, `tracked`)를 남긴다. 서버 재시작 전
파종분은 시작시각이 없어 `tracked=0`으로 분리하며, 충분한 실측 표본이 모이면 `farm_shop_audit.py`
의 가정 cycle을 교체한다.

## 메커니즘 (`crop/CropManager.java` + `crop/CropSpecs.java`)
순수 시간게이팅, **반복비용 없음**(물주기/비료 없음). `FARMLAND` 블록 위 `ItemDisplay`(모델)+
`Interaction`(히트박스)로 렌더 — CraftEngine 아님(CE는 제거 시 despawn 버그라 BlockShip 네이티브,
통발/배/짚라인과 같은 패턴).

**루프**: 씨앗 우클릭(파종, 씨앗1개 소모) → 5단계 시각성장(새싹→어린→성장→키큼→만숙,
`progress=(now-심은시각)/growSec`, 100틱=5초마다 재계산) → `progress≥1.0`이면 성숙+채팅알림 →
우클릭 수확(산출물 outQty개 지급+엔티티 제거, 1회성·재파종 없음) → **웅크리기+우클릭(미성숙 시)**=
조기 뽑기, 씨앗 1개 환불(완전손실 아님).

안전장치: 아래 농지가 흙으로 되돌아가면(마름/밟힘/파괴) 자동 뽑힘(성숙=산출물 지급, 미성숙=씨앗
환불) — 절대 "먹통"으로 안 남음.

## 작물 테이블 (`CropSpecs.java`, `crops.json`과 라이브 일치 확인 완료)
| 작물ID | 표시명 | growSec | 성장시간 | 산출물 | 수량 |
|---|---|---|---|---|---|
| 밀 | 특수 밀 | 1,200 | 20분 | WHEAT(mat:작물_밀) | 3 |
| 당근 | 특수 당근 | 1,800 | 30분 | CARROT(mat:작물_당근) | 2 |
| 감자 | 특수 감자 | 2,700 | 45분 | POTATO(mat:작물_감자) | 2 |
| 토마토 | 특수 토마토 | 3,600 | 1시간 | SWEET_BERRIES(mat:작물_토마토) | 2 |
| 양배추 | 특수 양배추 | 1,500 | 25분 | KELP(mat:작물_양배추) | 2 |
| 버섯 | 특수 버섯 | 2,400 | 40분 | BROWN_MUSHROOM(mat:작물_버섯) | 3 |
| 수박 | 특수 수박 | 86,400 | **24시간** | MELON_SLICE(mat:작물_수박) | 4 |

★**직접 판매가 없음** — 전 산출물이 `mat:작물_X` 마커만 달고 나오며 **요리 재료 전용**(cooking/
DishSpecs 레시피 인풋). 경제적 가치는 요리 시스템을 통해 간접 산정해야 함(아래 metrics 참조).
수박(24h)은 다른 작물(20~60분)과 규모가 3~4자릿수 다른 "하드 커밋" 작물.

재배 스킬(`SkillManager.FARMING`, 최대Lv50, `need=floor(need×1.06)`/레벨, 시작100): 수확 1회당
+8XP, 캡 없음(성장시간 자체가 자연 제약이라 무제한이어도 안전).

## 섬 작물 한도·업그레이드 비용

### 개인 (`island/IslandManager.java` L77-78)
```
CROP_LIMIT = {0, 4, 8, 12, 20, 32}
CROP_PRICE = {0, 0, 30000, 80000, 200000, 500000}
```
| 레벨 | 한도 | 비용 |
|---|---|---|
| 1(기본) | 4 | — |
| 2 | 8 | 30,000원 |
| 3 | 12 | 80,000원 |
| 4 | 20 | 200,000원 |
| 5(최대) | 32 | 500,000원 |
Lv1→5 총 810,000원, +28칸.

### 길드 (`guild/GuildManager.java` L50-51) — 정확히 개인×5 (AGENTS.md 컨벤션과 일치)
```
G_CROP_LIMIT = {0, 4, 8, 12, 20, 32}   // 한도는 개인과 동일
G_CROP_PRICE = {0, 0, 150000, 400000, 1000000, 2500000}
```
Lv1→5 총 4,050,000원(길드 전체 공유), +28칸.

## 스킬트리 농사 프록 (`SkillTreeManager.rollFarming`)
- 2배수확 확률(합산): `0.008×다수확 + 0.010×이삭 + 0.008×씨앗보존 + 0.006×속성재배`(랭크당, PRD아닌 단순롤)
- 보너스(강화 농산물, 풀스택 추가) 확률: `0.01 + 0.003×강화종자 + 0.004×희귀씨앗`(강화수확 랭크 게이트)
- 대풍년(PRD0.30%→4배) · 황금수확(PRD0.20%→max(3배)+보너스) · 생명의밭(PRD0.20%→max(3배)+씨앗환불)
- (기본) 풍년(PRD1.0%→2~3배) · 되살아남(PRD1.0%→씨앗환불)

## 섬상점 바닐라 농사 가격표 (`plugins/BlockShip/shop-items.json`)

`IslandShopGui`가 파일을 읽으면 이 JSON이 권위이며, 파일이 없거나 파싱에 실패할 때만
`economy/IslandShopGui.java`의 `defaultIslandCfg()`가 폴백으로 사용된다. 따라서 가격을 바꿀 때는
두 곳을 함께 맞춘다.

2026-08-20 감사에서 확인한 생산 품목은 다음과 같다.

| 생산 루프 | 출력·판매 경로 | 시간 모델 | 비고 |
|---|---|---:|---|
| 밀 | WHEAT + WHEAT_SEEDS | 10분/사이클 | 씨앗 부산물 포함 |
| 당근·감자·비트 | 작물 본체(+비트 씨앗) | 10분/사이클 | 감자는 독감자 손실 2% 반영 |
| 수박·호박 | MELON_SLICE/PUMPKIN | 15분/사이클 | 기존 가격표에 수확물이 빠져 있었음 |
| 사탕수수·대나무 | SUGAR_CANE/BAMBOO | 15분/5분 | 다단 성장의 보수적 평균 가정 |
| 코코아 | COCOA_BEANS | 15분/사이클 | 3단계 성숙 평균 |

가격 감사 실행:

```text
python3 .agents/skills/balance-audit/scripts/farm_shop_audit.py
```

이 도구는 최신 코호트 스냅샷의 Lv1 최적 낚싯대·작살 원/h를 읽고, 32칸 농장을 낮은 기준의
75%로 맞춘다. 32칸은 현재 특수작물 최대 한도와 같은 비교 단위일 뿐, 바닐라 경작지의 물리적
설치 한도를 새로 의미하지 않는다. 바닐라 경작지가 무제한이면 총수익도 슬롯 수에 비례해 늘어나므로,
실제 서버 목표를 유지하려면 추후 일반 경작지 한도 또는 섬 면적 한도를 별도로 결정해야 한다.

## 파일 위치
- 메커니즘: `JAVA/crop/CropManager.java`
- 스펙 테이블: `JAVA/crop/CropSpecs.java`
- 섬 한도: `JAVA/island/IslandManager.java` L77-78, L369-420
- 길드 한도: `JAVA/guild/GuildManager.java` L50-51, L543-554
- 스킬 프록: `JAVA/skilltree/SkillTreeManager.java` L396~571(rollFarming 구간)
- JSON: `JSON/crops.json`
