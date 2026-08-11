---
name: item-icons
description: >-
  Create professional Minecraft-style 16×16 item ICONS for inventory/GUI — fishing rods,
  reels, lines, hooks, baits, bobbers, equipment, crafting materials, and skill-tree /
  ability icons — including special effects like animated fire auras and glows, and wire
  them into the resource pack via item_model. Use whenever making item textures, equipment
  icons, part icons, skill icons, GUI icons, or "each rod should look unique" style
  requests — even if the user says "낚싯대 아이콘", "스킬 아이콘", "장비 이미지",
  "아이템 텍스처" without the words "pixel art". Sibling of the pixel-art skill (which
  covers placeable furniture/sprites); this one covers the inventory-slot stage:
  diagonal tool composition, slot-gray contrast, selective outline, grade escalation,
  and .mcmeta frame animation.
---

# Minecraft 아이템 아이콘 (인벤토리 무대 전용)

pixel-art 스킬의 동생. 그쪽이 "월드에 놓이는 가구/스프라이트"라면, 여기는 **인벤토리
슬롯(#8B8B8B, 18px) 위에서 읽히는 아이콘**이다. 무대가 다르면 규칙이 다르다 —
아이콘은 배경이 항상 회색이고, 항상 16px이고, 옆 칸에 바닐라 아이템이 나란히 뜬다.
바닐라 옆에 놓았을 때 이질감 없이 "한 등급 위"로 보이는 것이 목표.

## ★ 해부 스펙 — 품질의 근본 레버 (2026-07-20, 위반 금지)

**복잡한 물체(낚싯대·릴 등)는 그리기 전에 "모든 지형적 특성"을 데이터로 선언하고,
렌더러는 그 스펙만 읽어 그린다.** 이게 품질을 근본적으로 끌어올리는 유일한 방법이다.
이유: 스펙을 강제하지 않으면 낚싯대가 "불 달린 막대기"로 대충 끝나버린다. 해부학을
데이터로 박아두면 릴·라인가이드·휨·손잡이밴드·팁가이드·처지는 줄을 하나도 못 빠뜨린다.

`icon-forge/rod_anatomy.py`가 레퍼런스 구현(엔진+불의낚싯대 스펙). 낚싯대 해부 스키마:
`blank`(베지어 휨+테이퍼+재질램프) · `grip`(구간+감은밴드 wraps) · `buttcap` ·
`ferrule`(릴시트) · `reel`(스풀+크랭크) · `guides`(관절 링, 대에 밀착) · `tiptop` ·
`line`(릴→가이드 관통→팁→처짐) · `lure` · `cracks` · `fx`(tip_flame/lure_flame/glow).

세트 아키텍처: **한 종류(낚싯대 20종)는 스펙 하나의 변주일 뿐.** 사막=사암램프+태양참,
흑단=흑단램프+곧은 cp, 천공=수정램프+오로라glow. → 스펙 통일로 20종이 한 세트로
보이면서 각자 고유, 스크립트 한 번에 전부 재생성+애니메이션. (AI 생성으론 불가능한 일관성.)

이 접근에서 배운 렌더링 함정(전부 rod_anatomy.py에 반영됨):
- **실린더 셰이딩은 법선/광원 투영으로.** 빈이웃 판정(가장자리=밝음)은 얇은 구간에서
  전부 하이라이트가 돼 금색 막대가 된다. `proj=(픽셀−중심선)·광원방향/반경`으로 램프 인덱스.
- **글로우/오버레이는 픽셀당 1회만.** 촘촘한 중심선 샘플마다 재적용하면 20배 누적돼
  나무가 순금이 된다. 마스크 픽셀을 1회 순회.
- **라인 가이드는 대에 밀착한 작은 링.** 3~4px 띄우면 색종이처럼 흩어진다(발 1px+링 ro1.5).
- **가이드·줄은 한 면으로.** 스피닝릴=릴과 가이드 같은 쪽 → 줄이 대를 안 가로지른다.
- **장식 색은 한 곳에만.** 빨강이 손잡이+대에 다 있으면 산만 → 레퍼런스대로 손잡이만.

## 루프 — 매번 이 순서

1. **정체성 테이블 먼저.** 아이콘 배치(batch)는 그리기 전에 표부터 만든다:
   `이름 → 실루엣 모티프 / 재질 램프 / 포인트 색 / 참(charm·장식) / fx`.
   이름이 곧 브리프다 — "사막 낚싯대"면 사암+금테+태양 참, "여명"이면 새벽 그라데이션.
   84종을 눈감고 그리기 시작하면 뒤에서 반드시 서로 닮아진다. 표에서 겹침을 먼저 죽인다.
2. **팔레트는 근거에서.** pixel-art 스킬의 `palette.py`(휴시프트 램프)와
   `palette_from_image.py`(레퍼런스 추출)를 그대로 쓴다. 재질당 램프 4~5색.
   레퍼런스 보드도 pixel-art와 공유(`pixel-forge/refboard/`) — 장비 아이콘 레퍼런스는
   MCModels/BuiltByBit 장비팩 제품 이미지가 최고다(참고만, 파일 재배포 금지).
3. **실루엣 = 카테고리 문법 + 개체 정체성.** 아래 「카테고리 문법」의 구도를 따르되,
   개체마다 실루엣이 달라야 한다(색칠놀이 금지 — pixel-art와 동일한 오너 규칙).
4. **형태 셰이딩.** 광원 좌상단 고정. `iconlib.shaft`는 원통 셰이딩(윗면 라이트/아랫면
   코어섀도)을 브러시에 내장했고, 덩어리는 `selout`(아래·오른쪽=어두운 램프,
   위·왼쪽=림라이트)으로 마감한다. 퓨어 블랙 외곽선 금지.
5. **fx는 실루엣 다음.** 오오라·글로우는 본체가 완성된 뒤 실루엣 *바깥*에만
   (`fx.py`). 애니메이션은 바닐라 `.mcmeta` 세로 스트립 — 인벤토리에서 실제로 일렁인다.
6. **렌더 & 크리틱 — 슬롯 목업이 1차 진실.** `icon_lint.py`(슬롯 대비·대각 구도·점유율
   객관 게이트) → `slot_preview.py`(바닐라 GUI 규격 목업) → 애니는 `fx.save_gif`.
   최종 진실은 RP 배포 후 인게임: 아이템 지급받아 인벤토리 스크린샷(references/wiring.md).
7. **자기비평 루프 — 유저에게 검수 떠넘기지 말 것(★2026-07-20 오너 강피드백).**
   렌더 → **내 눈으로 직접 본다** → 결함을 해부 체크리스트로 잡는다(굵기 단차 있나? 줄이
   팁에서 아래로 처지나 대 위로 가나? 릴이 스풀+크랭크로 읽히나 덩어리인가? fx 과한가?
   광원 일관? 슬롯32px에서 읽히나?) → 고친다 → 다시 본다. **통과할 때까지 혼자 3~4패스
   돌리고, 통과한 것만 유저에게 보여준다.** 반쯤 된 렌더를 매번 보여주며 유저를 검수자로
   쓰는 건 금지. 첫 패스가 마지막인 적은 없다.

## 카테고리 문법 — 모티프 소유권

부품 6종이 인벤에 섞여 뜨므로, **카테고리마다 고유 구도를 소유**해야 한눈에 구분된다:

| 카테고리 | 구도 | 소유 모티프 | 금지 |
|---|---|---|---|
| 낚싯대 | ↗ 대각, 휜 샤프트+그립+줄 | 샤프트 재질·그립 랩·팁 참 | 릴 크게 그리기(릴 카테고리 침범) |
| 릴 | 중앙 원형 스풀+크랭크 | 스풀 패턴·크랭크 모양 | 대각 막대 |
| 줄 | 코일 타래(원형 감김) | 줄 색·매듭 | 직선 한 가닥(안 읽힘) |
| 바늘 | 훅 클로즈업(J자 대형) | 미늘·고리·독 방울 | 너무 얇게(2px 두께 유지) |
| 미끼 | 생물/단지 정면 | 생물 실루엣·용기 | 대각 구도 |
| 찌 | 수직 부표+수선 1줄 | 몸통 형태·안테나 | 대각 구도 |

스킬 아이콘(특성 트리)은 **배지 문법**: 원형/방패 필드 + 중앙 굵은 글리프 1개 +
반짝이 ≤2. 글리프가 12×12 안에서 한 형태로 읽혀야 한다(만선=그물 위 물고기,
거대어=대형 물고기 옆모습 등). 티어 상승은 필드 램프+테두리 재질로.

## 등급 사다리 (E→S) — 실루엣은 유일, 화려함은 등급

같은 카테고리 안에서 등급은 **장식의 계단**으로 보여준다. 실루엣 유일성 원칙과 공존:

- **E**: 삐뚤빼뚤·무장식(폴리라인, 그립 없음). 초라함도 정체성이다.
- **D**: 곧아지고 깨끗해짐. 마디/밴드 1종.
- **C**: 그립 랩 + 재질 고유색 등장.
- **B**: 금속 페룰 링, 포인트 색 1개.
- **A**: 참(charm) 부착 — 태양 부적, 여명 오브 등 이름의 모티프를 물체로.
- **S**: 금 와인딩/보석 + fx(글로우·애니 오오라). 서버 상징색 허용.

## fx 규칙

- 오오라 픽셀 ≤ 본체의 25%, 실루엣 바깥만, 본체 절대 안 덮음.
- 애니메이션: 4프레임, frametime 3(≈0.15s/프레임)이 기본. 앵커 고정+높이만 흔들기
  (`fx.fire_aura`가 보장). 반투명은 글로우 헤일로만, lint가 개수 감사.
- 남발 금지: 한 상점 GUI에 애니 아이콘이 3개 넘게 보이면 싸구려 슬롯머신이 된다.
  S급과 특수 미끼에만.

## 도구 (scripts/)

- `iconlib.py` — 브러시: `qbez`/`polyline`→`cells`→`shaft`(테이퍼+원통 셰이딩),
  `grip`, `ring_at`, `hang_line`, `disk`, `sparkle`, `selout`, `grade_colfn`(그라데이션 샤프트).
- `fx.py` — `fire_aura`(프레임들), `glow_halo`(정적), `save_anim`(스트립+.mcmeta),
  `save_gif`(리뷰용).
- `icon_lint.py <png...> --category tool|prop|badge` — 슬롯 대비·대각 구도·점유율·
  색 수·반투명 감사. exit code = 경고 수.
- `slot_preview.py <out> <png...>` — 바닐라 GUI 규격 슬롯 목업(1차 진실).
- 색/뷰어는 pixel-art 스킬 것을 공유: `palette.py`, `palette_from_image.py`,
  `view.py`, `contact.py`, `compare.py`.

## 파이프라인 (icon-forge/)

pixel-forge와 같은 구조의 매니페스트 파이프라인 — `icon-forge/`:
`manifest.json`(정체성 테이블의 코드화) → `painters.py`(개체당 페인터, git 추적) →
`build.py`(페인트→fx→린트→콘택트+슬롯 목업→ `--install`로 RP 배치+model/items 정의 생성).
색칠놀이 하드가드 포함(같은 페인터+색 kwargs만 다름 = 빌드 실패). 페인터를 /tmp에
쓰지 말 것 — PNG는 남고 소스는 죽는다.

## RP 연결 (요약 — 상세 references/wiring.md)

카지노 카드로 검증된 규약 그대로:
텍스처 `assets/minecraft/textures/item/barkan_icon/<id>.png`(+`.mcmeta`) →
모델 `assets/barkan/models/barkan_icon/<id>.json`(layer0=`minecraft:item/barkan_icon/<id>`) →
아이템 정의 `assets/barkan/items/barkan_icon/<id>.json` →
플러그인에서 `meta.setItemModel(NamespacedKey("barkan","barkan_icon/<id>"))`.
GUI 전용(스킬 아이콘)은 GUI 아이템에 setItemModel만 하면 끝(재질 교체 불필요).

## 딥 크래프트

`references/icon-craft.md` — 바닐라 아이콘 해부(대각 관례·외곽선 실측), 재질 램프
표준표(목재/대나무/흑단/사암/금/수정/카본), 오오라 설계, 배지 구도, 아마추어 티 체크리스트.
