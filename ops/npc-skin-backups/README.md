# NPC 스킨 로컬 백업

**2026-09-01 신설.** 오스카(&b[말 대여])의 스킨 텍스처가 Mojang 텍스처 서버(`textures.minecraft.net`)에서
blob 자체가 사라져(404) 접속 클라이언트에 기본 스티브로 보이던 사고 이후, prod의 모든 Citizens
NPC 스킨을 로컬 PNG로 백업해 둔 것. Citizens skintrait은 URL(+서명)만 저장하고 실제 픽셀은
Mojang이 들고 있으므로, 그 blob이 나중에 또 사라지면 이 백업 없이는 **처음부터 다시 그리는 것**
말고는 복구 수단이 없다.

## 구성

- `<citizensId>_<이름>_<hash8>.png` — 각 NPC의 스킨 원본(64x64), 감사 시점 기준 전부 200 정상.
- `manifest.json` — `[{cid, name, hash}]`. 감사 스크립트가 재실행할 때 대조 기준.

## 감사 결과 (2026-09-01)

prod `Citizens/saves.yml`의 PLAYER 타입 NPC 186개 전수 조사:

- **185개** — `textureRaw`의 텍스처 URL 전부 200 정상 → 이 폴더에 원본 백업.
- **오스카(cid43, &b[말 대여])** — 원래 blob 소실(404), `skin-forge/oscar.py`로 재제작 후 적용 완료.
- **요한(cid162, &a[Q] 길드접수원, 튜토00 지급 NPC)** — `traitnames`엔 skintrait이 나열돼 있는데
  실제 데이터가 통째로 없었다(오스카보다 심한 케이스 — blob이 아니라 애초에 스킨 자체가 없었음).
  신규 유저가 접속 후 가장 먼저 마주치는 NPC 중 하나라 임팩트가 컸다.
  `skin-forge/johan.py`로 재제작 후 적용 완료.
- **cid150(&b페리선장)** — npc.json에 **미등록**, 좌표 (0,0,0), skintrait도 없음. 다른 곳에 살아있는
  "페리선장"(cid4 등)이 따로 있어 이건 죽은/유령 엔트리로 보임. 스킨 문제 범주는 아니라 이번엔
  건드리지 않음 — 필요하면 별도로 정리할 것(spawned 상태라 실제로 스폰될 가능성 있음, 미확인).

## 복구 방법 (blob이 또 사라졌을 때)

1. 이 폴더에서 해당 `<citizensId>_*.png`를 찾는다.
2. prod에 올리고 MineSkin 업로드:
   ```
   scp <png> ubuntu@<prod>:/tmp/ && ssh ubuntu@<prod> \
     'curl -s -X POST https://api.mineskin.org/generate/upload -F "file=@/tmp/<png>" -F "variant=classic"'
   ```
3. 응답 `hash`로 `npc skin --id <citizensId> --url https://textures.minecraft.net/texture/<hash>`.
4. `citizens save` 후 saves.yml 되읽기로 반영 확인(RCON `ok`는 증거 아님) → `citizens reload`.

상세 절차·함정은 스킬 `npc-skin-forge`의 SKILL.md·`references/lessons.md` 16~17장 참고.

## 재감사 스크립트

전체 185개 URL이 아직 살아있는지 재확인하려면 (수백 개라 서버에 부담 주지 않게 병렬 12개 제한):

```python
# saves.yml → cid/name/textureRaw URL 추출 후 HEAD 요청으로 상태 확인.
# scratchpad의 extract_skins.py + check_status.py 참고(세션 한정 파일이라 이 저장소엔 없음 —
# 다시 필요하면 같은 로직으로 재작성).
```
