# NPC 스킨 prod 배포

`skin-forge/out/<스킨이름>.png` 을 Citizens NPC 에 입히는 절차. 158장 규모라
손으로 못 한다.

## 권위
* **`npc-cid-map.json`** = `{스킨이름: Citizens cid}`. ★cid 는 **prod 실측값**이어야
  한다 — dev cid 를 적어 두면 적용 시 Citizens 가 `Couldn't find any NPC with ID`
  를 뱉고 그 NPC 만 조용히 빠진다(2026-08-22 `tf_healer` 가 901 로 적혀 있었고
  prod 실제 cid 는 122 였다. 이름으로 찾아 고쳤다).
* 스킨 적용 결과의 권위는 **`plugins/Citizens/saves.yml` 의 `textureRaw`** 다.
  RCON 이 `§a...` 를 돌려주는 건 증거가 아니다 — `verify.py` 로 되읽어 확인한다.

## 절차
1. 스킨을 커밋한다 (★prod 는 커밋본에서 배포).
2. `<cid>.png` 이름으로 prod `/tmp/npcskins<N>/` 에 올린다.
3. `deploy-skins.sh` (DIR 을 그 폴더로) + `deploy-skins-cron.sh` 를 두고
   `crontab */5` 로 돌린다. **tmux 는 쓰지 말 것** — MC 재시작에 세션이 날아간다
   (2026-08-20 16:05 사고). cron+flock 은 재시작을 넘어 이어진다.
4. 파이프라인: MineSkin 업로드 → `npc skin --id <cid> --url` → `citizens save`
   → `verify.py` 3회차 재적용 → `citizens reload` → `bm reload` → `npc모델재부착`.
   ★리로드 순서 지킬 것. `bm reload` 없이 재부착하면 이름표가 사라진다.
5. **검증 루프는 3회차에서 끝난다** — 3회차에 남은 건이 있으면 재적용만 되고
   확인은 안 된 상태로 `=== 완료 ===` 가 찍힌다. 끝난 뒤 `verify.py` 를 한 번 더
   돌려 0건인지 볼 것.

## 함정
* `npc skin --url` 은 **선택 상태를 안 쓰는** 유일한 경로다. 콘솔/RCON sender 는
  NPC 선택을 유지하지 못해서 `mc_npc_set_skin` 이 `ok:true` 를 주고도 0건 적용된다.
* MineSkin 응답의 텍스처 해시는 **최상위 `hash`** 필드다(`data.texture.url` 없음).
* 업로드 간 8초, 적용 간 10초 쉬어야 레이트리밋에 안 걸린다.
