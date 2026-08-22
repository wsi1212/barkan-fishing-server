# 유물 감정 · 말 대여소 전용 배경

두 화면 모두 Paper 1.21의 27칸 GUI다. 배경은 제목 글리프 12타일(704×672)로 굽고,
아이템과 lore는 Java가 런타임에 올린다. 그림에 글자나 아이템을 구워 넣지 않는다.

## 좌표 계약

| 화면 | 실제 코드 슬롯(0-based) | 화면에서 보이는 의미 |
|---|---:|---|
| 유물 감정 | 13 | `CLAY_BALL` 기반 미감정 유물 감정 버튼/입력 자리 |
| 유물 감정 | 26 | `BARRIER` 닫기 |
| 말 대여소 | 4 | 비움 — 화면 슬롯 5는 장식 배경으로 채움 |
| 말 대여소 | 10·12·14·16 | ImageGen 기반 `horse_pony`·`horse_brown`·`horse_white`·`horse_black` |
| 말 대여소 | 22 | 대여 중일 때 `ui_gui_horse` 소환 버튼 |

화면 슬롯 번호로는 유물 감정 중앙 입력이 14번, 닫기가 27번이다. 말 4종은
11·13·15·17번으로 한 칸씩 띄워지고, 화면 슬롯 5번은 비어 있는 장식 영역이다.
플레이어 인벤토리(아래 4줄)는 배경이 건드리지 않는다.

## 산출물

- `src/artifact/bg_source.png` — 사피르 사암 감정실
- `src/horse/bg_source.png` — 목재 마구간 진열대
- `src/artifact/_preview_items.png` — 실제 `clay_ball`·`barrier` 아이콘 목업
- `src/horse/_preview_items.png` — ImageGen 기반 말 4종 + 실제 소환 버튼 목업
- `src/*/_order.png` — 좌표와 컨셉을 합친 발주 시트
- `src/*/_glyph.txt` — Java 제목에 연결할 글리프 문자열

## 재생성·검증

```bash
python3 gui-forge/build_artifact_horse_bg.py
python3 gui-forge/build_plate.py artifact horse
python3 gui-forge/mock_artifact_horse_items.py
python3 gui-forge/verify_artifact_horse_bg.py
python3 ops/build-prod-rp.py
cd /Users/user/development/blockship-plugin && ./gradlew build
```

`verify_artifact_horse_bg.py`는 캔버스 크기·불투명도·실제 슬롯 영역·12개 글리프 provider·256px
타일 제한을 검사한다. `ops/build-prod-rp.py`는 배포하지 않고 slim ZIP만 `/tmp`에 만든다.

## Java 연결

- `com.blockship.crafting.ArtifactAppraisalGui` → `GLYPH_ARTIFACT`
- `com.blockship.horse.HorseRentalGui` → `GLYPH_HORSE`

두 클래스의 `GuiTitle.of(...)`가 이 배경을 실제 제목에 얹는다. Java jar와 리소스팩은 같은
변경 묶음으로 배포해야 한다.
