# 캔버스 범용화 실행 명세 (2026-08-17 결정, 미착수)

길드 엠블럼 전용이던 지도 캔버스를 **누구나 아무데나 설치하고 누구나 그리는** 범용
시스템으로 빼고, 길드는 그 캔버스에서 나온 지도를 **등록**만 하게 한다.

## 확정된 결정 (유저 응답)
1. **범용 캔버스로 완전 대체** — `/길드 엠블럼 설치` 경로는 없앤다. 기존에 캔버스를 깐
   길드(prod `ㄱㅣ모띠`, `guild_world -10 66 1 EAST`, frameUuid `7d39e3f8-…`)는 그 액자를
   범용 캔버스로 승계한다(소유자=당시 길드장).
2. **문양 등록 권한은 부길드장 이상 고정** — 설정 GUI 토글 신설하지 않는다.
   지금 길드엔 이름붙은 권한 체계가 없고 설정 GUI가 전부 `isVice` 하드코딩이라 그 관례를 따른다.

## 지금 구조 (출발점)
| 요소 | 현재 위치 |
|---|---|
| 팔레트 20색 + 붓 규격 | `guild/EmblemPalette` (참조 6파일: GuildGui·GuildData·GuildManager·GuildCommand·GuildThumbnailService) |
| 설치/철거 | `GuildGui.installEmblemCanvas` / `removeEmblemCanvas` |
| 칠하기 | `GuildGui.onEmblemFrameClick` — 액자 bbox 레이트레이스 → 픽셀, 액자 방향별 좌우 반전 보정 포함 |
| 도구판 GUI | `GuildGui.openEmblemTools` / `paintEmblemTools` / `clickEmblemTools` + `EmblemToolHolder` |
| 되돌리기 | `PaintState.undo` (`Deque<Stroke>`, `UNDO_DEPTH=40`) |
| 저장 | `GuildData.emblemCanvas` (base64 byte[128*128]) + 좌표/facing/frameUuid |
| 파생 | 64×64(`emblemCanvasPixels`)·8×8(`emblemPixels`) — 저장 때마다 캔버스에서 재생성 |
| 액자 보호 | `GuildGui.onEmblemFrameBreak`(HangingBreakEvent) · `onEmblemFrameClick` |
| 청크 복원 | `GuildGui.onEmblemChunkLoad` → `refreshInstalledEmblemFrames` |
| 웹 색표 | `EmblemPalette.writePaletteJson` → `emblem-palette.json` → `/api/ranking` |

캔버스 규격(체스 `PaintingManager` 와 동일): 128×128, 20색, 붓 지름 1·3·5·9, 지우개,
배경 = 지도 종이색 `MapPalette.matchColor(238,230,207)`.

## 목표 구조
```
canvas/
  CanvasPalette.java     ← guild/EmblemPalette 이동 (참조 6곳 갱신)
  Canvas.java            ← id, world, x,y,z, facing, frameUuid, ownerUuid, ownerName, byte[16384]
  CanvasManager.java     ← 영속(canvases.json) + 설치/철거 + 칠하기 + 렌더 + 액자보호 + 청크복원
  CanvasToolGui.java     ← 도구판(스와치20·붓4·지우개·되돌리기·전체지우기)
guild/
  GuildData              ← 캔버스 좌표/frameUuid 필드 제거, 엠블럼 픽셀 + 파생만 유지
  GuildGui               ← 캔버스 코드 전부 제거, "문양 등록" 진입만 남김
```

### 명령어
- `/캔버스` (플레이어) — `설치` · `제거` · `도구`. 두벌식 영타 별칭 + 탭 완성 필수(CLAUDE.md 규약).
  - 설치: 바라보는 벽에 액자+지도. **길드 무관, 누구나.**
  - 제거: **설치자 본인 또는 OP만.**
  - 도구: 근처(또는 조준한) 캔버스의 도구판 열기.
- `/길드 문양등록` — 조준한 캔버스의 현재 픽셀을 **복사**해 길드 엠블럼으로 등록.
  - 권한: MASTER · VICE_MASTER.
  - ★복사(스냅샷)다. 링크가 아니다 — 누구나 그릴 수 있으므로 링크면 등록 후에도 남이 문양을 바꿀 수 있다.

### 그리기 권한
누구나. 캔버스는 공용 낙서판이다. 액자 파괴·회전만 보호(설치자/OP 외 차단).

## 마이그레이션
기동 시 1회: `GuildData` 에 `emblemCanvasFrameUuid` 가 있는 길드를 찾아
① 그 액자를 범용 캔버스로 등록(owner=길드장 UUID) ② 픽셀 승계 ③ 길드 쪽 캔버스 좌표 필드 정리.
prod 대상은 1건(`ㄱㅣ모띠`), dev 0건. **픽셀은 현재 전부 빈칸이라 실질 승계 데이터는 없다** —
그래도 액자 자체는 살려야 유저가 설치물을 잃지 않는다.

## 검증 항목 (봇으로 재현 불가 — 사람이 직접)
- 아무 벽에나 `/캔버스 설치` → 액자+지도 생성
- 길드 없는 유저가 남의 캔버스에 그려짐
- 액자 파괴가 설치자/OP 외에 막힘
- `/길드 문양등록` 이 부길드장 이상만 되고, 등록 후 원본 캔버스를 고쳐도 길드 문양은 안 바뀜
- 길드 목록·랭킹·웹 미리보기에 등록한 문양이 뜸
- 재시작·청크 언로드 후 캔버스 그림 유지

## 주의
- `EmblemPalette` 이동 시 `emblem-palette.json` 파일명·`/api/ranking` 계약을 바꾸지 말 것(웹이 읽는다).
- 스와치 20색이 서로 다른 지도 바이트로 스냅되고 배경과 안 겹치는 성질은 기동 시 검산으로 지킬 것
  (겹치면 `indexOf` 의 `putIfAbsent` 가 색을 조용히 삼킨다).
- 액자 방향별 좌우 반전 보정(NORTH/EAST 는 반전)은 기존 코드에서 그대로 가져올 것 —
  다시 유도하면 벽 방향에 따라 좌우가 뒤집힌다(이미 한 번 고친 버그).
