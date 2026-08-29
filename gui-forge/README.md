# gui-forge — GUI 배경판 발주·검수·굽기 파이프라인

마크 상자 창(GUI)의 **배경 그림**을 만드는 곳이다. 발주서를 굽고, 받은 그림을 검수하고,
글리프로 쪼개 리소스팩에 넣고, 플러그인이 쓸 문자열을 뽑는 데까지가 여기 몫이다.

> **이 문서가 왜 생겼나 (2026-08-14)**
> 스크립트마다 독스트링은 훌륭한데 **어디서 시작하는지가 어디에도 없었다.** 최상위 문서
> (CLAUDE.md·docs-index.md) 어느 쪽도 `gui-forge` 를 언급하지 않아서, 새 세션은 이 파이프라인이
> 존재하는지조차 몰랐다. 순서와 현황을 한 장에 모은다.

---

## 한 화면이 지나가는 길

```
① 배치 정의     make_page_layouts.py 의 PAGES 에 항목 추가   ← 슬롯 번호의 권위
② 뼈대판        python3 make_templates.py <화면>             → src/<화면>/_template.png
   좌표 도면     python3 make_page_layouts.py                 → src/<화면>/_guide.png
③ 발주서        python3 make_order_sheets.py <화면>          → src/<화면>/_order.png  ★넘길 건 이것 하나
④ (그림 받음)   받은 파일을 src/<화면>/bg_source.png 로
⑤ 검수          python3 check_align.py <화면> <납품파일>     → _align_check.png   ★받자마자
   수치 검사     python3 audit_all.py <화면>
⑥ (필요시 보정) 아래 「보정 스크립트 고르기」
⑦ 굽기          build_plate.PLATES 에 등록 → python3 build_plate.py <화면>
                → 리소스팩 텍스처 12장 + font/gui.json + src/<화면>/_glyph.txt
⑧ 자바 연결     _glyph.txt 를 util/Plates.java 상수로 → 화면 코드가 Plates.title(p, 상수, "제목")
⑨ 배포          리소스팩 먼저(맥 ops/rp-deploy.sh) → 그다음 플러그인
```

**★⑨ 순서를 뒤집지 말 것.** 팩보다 플러그인이 먼저 나가면 배경이 안 그려지고 제목 자리에
네모(두부)만 뜬다. 글리프는 팩에 있고 코드가 그걸 가리키기만 하기 때문이다.

---

## 새 세션에 발주 맡기기

**`src/<화면>/_order.png` 한 장이면 된다.** 그게 설계 의도다 —
`make_order_sheets.py` 독스트링:

> 발주서(.md)와 뼈대판(.png)을 따로 넘기면 **그림을 못 찾는 일이 생긴다**(2026-08-08).
> 그림 한 장에 지시문까지 얹어 두면 **그 한 장만으로 작업이 된다.**

왼쪽이 실제 크기 뼈대판(덧칠할 판), 오른쪽이 규칙·컨셉이다. 오른쪽은 잘라내고 왼쪽만 줘도 된다.
`_template.png` 는 이미 발주서 왼쪽에 들어가 있고, `_guide.png` 는 슬롯 번호가 적힌 **우리 도면**이라
넘길 필요가 없다.

받으면 **가장 먼저** `check_align.py` 를 돌린다. `check_align.py` 독스트링이 그렇게 못박아 뒀다 —
*"눈으로는 멀쩡해 보여도 아이콘이 액자 밖으로 나가므로 받자마자 이걸 돌린다."*

### 정렬 수치 읽는 법

`audit_all.py` 는 칸마다 (왼, 오, 위, 아) 오차를 낸다. **절대값이 아니라 편차를 본다.**

```
guildupgrade   21칸  패턴 1종  (-4,+4,-4,+4)   ← 합격 (전 칸 동일)
dexisland      17칸  패턴 1종  (-4,+4,-5,+4)   ← 이미 나간 판
dextab         33칸  패턴 1종  (-5,+5,-4,+3)   ← 이미 나간 판
```

`-4/+4` 는 **정상이다.** 액자 구멍이 72px 칸에 맞고 아이콘이 그 안 64px 로 앉는다는 뜻이고,
바닐라 슬롯 비율(18px 칸 / 16px 아이템)과 같다. 나간 판들이 전부 이 값이다.
**문제는 칸마다 값이 다를 때다** — 그건 격자 피치가 어긋났다는 신호다.

---

## 보정 스크립트 고르기

받은 그림이 어긋났을 때 쓴다. 넷이 이름이 비슷한데 하는 일이 다르다.

| 스크립트 | 언제 | 하는 일 |
|---|---|---|
| `prep_delivery.py` | 캔버스 크기가 다를 때 | 리사이즈 + 구간 보정 |
| `fit_plate.py` | 격자만 늘리고 테두리는 두고 싶을 때 | 구간별 재배치 |
| `refit_plate.py` | 칸마다 그림이 다른 판(아이스박스·우편함) | 블록째 배율로 옮김 (8px→6px 정도까지) |
| `resnap_plate.py` | **칸 액자가 전부 같은 판** | 액자 한 칸을 떠서 모든 칸에 다시 찍음 → 오차 0 |
| `assemble_plate.py` | 배경과 액자를 따로 받았을 때 | 코드가 좌표를 잡아 조립 (`.assembled` 마커) |

`resnap_plate.py` 가 가장 정확하지만 **칸마다 그림이 다른 판에는 쓰면 안 된다** — 하나로 덮어
그 다양성이 사라진다. 그런 판은 `refit_plate.py`.

---

## 화면 현황 (2026-08-14)

`○` 있음 · `·` 없음 · `★` 조립판(인벤 격자 덧그리기 건너뜀)

| 화면 | 가이드 | 발주 | 납품 | 검수 | 글리프 | 조립 | PLATES |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| common6 | ○ | · | ○ | · | ○ | | · |
| cooking | ○ | · | ○ | ○ | ○ | | ○ |
| crafting | ○ | ○ | ○ | ○ | ○ | | ○ |
| dexfish | ○ | ○ | ○ | ○ | ○ | | ○ |
| dexisland | ○ | ○ | ○ | ○ | ○ | ★ | ○ |
| dexmain | ○ | ○ | ○ | ○ | ○ | | ○ |
| dextab | ○ | ○ | ○ | ○ | ○ | ★ | ○ |
| dialogue | · | ○ | · | · | · | | · |
| disassemble | ○ | ○ | ○ | ○ | ○ | | ○ |
| enhance | ○ | · | ○ | ○ | ○ | | ○ |
| fish_shop | ○ | · | ○ | · | ○ | | · |
| fishing_success | ○ | · | ○ | · | · | | · |
| forge | ○ | ○ | ○ | · | ○ | | ○ |
| guild | ○ | · | ○ | · | ○ | ★ | ○ |
| **guildupgrade** | ○ | ○ | ○ | ○ | ○ | | ○ |
| icebox | ○ | · | ○ | · | ○ | | · |
| iceshop | ○ | ○ | ○ | ○ | ○ | | ○ |
| inventory | · | ○ | · | ○ | · | | · |
| mailbox | ○ | · | ○ | ○ | ○ | | ○ |
| menu | ○ | · | ○ | · | ○ | | · |
| myinfo | ○ | · | ○ | · | ○ | | · |
| npcdialog | ○ | ○ | ○ | ○ | ○ | | ○ |
| questlist | ○ | ○ | · | · | · | | · |
| questnpc | ○ | ○ | · | · | · | | · |
| shop | ○ | · | ○ | · | ○ | | · |
| skillhub | ○ | ○ | ○ | ○ | ○ | | ○ |
| skilltree | ○ | ○ | · | ○ | ○ | | ○ |
| smithy | ○ | ○ | ○ | · | ○ | | ○ |
| workbench | · | ○ | ○ | · | ○ | ★ | ○ |

`icons` · `status_icons` · `titles` 는 화면이 아니라 아이콘 소재 폴더다.

**전용판을 굽지 않는 화면이 훨씬 많다.** 목록형(랭킹·목록·가입신청 등)은 내용이 매번 달라서
공용판(`Plates.COMMON6`)을 그대로 쓴다 — `codex-brief-gui3.md` 의 원칙이다:
*"나머지 40여 개 화면은 목록형이라 내용이 매번 달라서 공용판을 그대로 쓴다."*
**슬롯 자리가 고정된 화면만** 전용판 후보다.

---

## 코드포인트 장부

글리프는 `build_plate.PLATES` 가 화면마다 16칸씩 잡아 쓴다. 겹치면 다른 화면 배경이 깨진다.

```
E620 낚시창 · E650 판매창 · E660 공용6행 · E670 메뉴 · E680 내정보 · E690 상점 · E6A0 아이스박스
E6B0 강화 · E6C0 우편함 · E6D0 요리 · E6E0 대장간 · E6F0 조합대
E700 제목글리프(예약) · E710 분해 · E720 재료제작 · E730 아이스상점 · E740 특성트리 · E750 스킬허브
E760 도감표지 · E770 도감속장 · E780 물고기도감 · E790 수집품섬 · E7A0 NPC대화
E7B0 장비작업대 · E7C0 길드허브 · E7D0 길드업그레이드     ← 다음 빈 자리 E7E0
```

---

## 함정

- **★맥 경로 의존** — 스크립트 27개가 폰트를 `~/development/barkan-resourcepack/assets/barkan/font/aggro_bold.ttf`
  에서 찾는다. 맥이 아닌 세션(웹·모바일)에서는 리소스팩을 먼저 받아야 한다:
  ```bash
  git clone --depth 1 --filter=blob:none --sparse \
      https://github.com/wsi1212/minecraft-fish-resource-pack ~/development/barkan-resourcepack
  cd ~/development/barkan-resourcepack
  git sparse-checkout set assets/barkan/font assets/barkan/textures/gui
  ```
  폰트가 없어도 스크립트는 안 죽는다 — `ImageFont.load_default()` 로 조용히 넘어가고
  **한글이 전부 깨진 발주서가 나온다.** 그래서 더 위험하다.
- **글자를 그리지 말 것** — 제목·라벨은 코드가 찍는다. 발주서에도 적혀 있다.
- **투명 픽셀 0** — 투명하면 바닐라 상자 배경이 비친다(모든 상자 GUI가 공유하는 텍스처라 교체 불가).
- **플레이어 인벤 영역에 격자·장식 금지** — 바닐라가 자기 격자를 그 위에 그린다.
- **`_template.png` 와 `_guide.png` 의 인벤 상자가 4px 다르다.** `make_templates.py` 는 30,
  `make_page_layouts.geom()` 은 31 을 쓴다. 굽는 쪽(`build_plate`·`assemble_plate`·`audit_holes`)은
  전부 30 이라 **31 쓰는 쪽이 소수파**(`make_page_layouts`·`make_guide`·`check_align`).
  발주에는 지장 없지만(1 GUI px, 게다가 "그리지 마" 영역 경계) 언젠가 정리할 것.
- **슬롯 번호를 코드로 일괄 치환하지 말 것** — 같은 숫자가 화면마다 다른 뜻이다.
  2026-08-14 에 `inv.setItem(45, …)` 를 파일 전체에서 바꿨다가 엠블럼 편집기 저장 버튼이
  캔버스 픽셀 자리로 갔다. **컴파일도 부팅 스모크도 이걸 못 잡는다.**
