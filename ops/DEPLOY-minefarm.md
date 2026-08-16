# 배포 런북 — 마인팜 라인 + 미적용 패치 2종 (2026-08-16)

원격 세션에서는 **prod에 손이 닿지 않는다**(SSH 키 없음, 22 차단). 아래는 **Mac에서** 도는 순서다.

---

## ⛔ 먼저 — 지금 그대로 쏘면 안 되는 것 셋

### 1. 오스발트 NPC가 아직 없다 → 퀘스트 8개가 죽은 채로 올라간다

`npc.json`의 `citizensId`가 `""`다. 데이터만 올리면 퀘스트는 존재하는데 **주는 사람이 없다.**
해롭진 않지만 의미도 없다. Citizens NPC를 먼저 세울 것:

```
/npc create 오스발트          # 스폰마을 밭·헛간 근처, 낚시터에서 떨어진 곳
/npc list                     # 부여된 id 확인
```
그 id를 `npc.json`의 `오스발트.citizensId`에 넣고, Citizens `saves.yml`의 `name`을
`&a[Q] 오스발트`로 맞춘다(초록 = 퀘스트 주는 NPC. **stop → 편집 → start**).
반영은 `/npc동기화`.

### 2. 자바 패치 2종이 dev에서 한 번도 안 돌았다

빌드만 통과했지 **실행은 안 해 봤다.** 특히 이번 패치가 얹는 것:
- `IslandFarmlandCounter` — `BlockPlace`/`BlockBreak`/**`BlockFromTo`**(물 흐름 = 핫패스)에
  리스너를 건다
- 비동기 청크 스냅샷 스캔 태스크
- `PlayerInteractEvent` 핸들러 하나 추가(`CropManager.onBundleOpen`)

CLAUDE.md의 「★자동배포=미검증 jar도 그대로 적용되니 **dev 테스트 후** 스테이징할 것」이
정확히 이 경우다. **`~/deploy-dev.sh`로 dev에 먼저 올리고** 섬에서 밭 갈아 보고 prod로 갈 것.

### 3. 「싹다」의 범위 — 파이프라인 20개는 마인팜만이 아니다

19번만 마인팜이다. 1~18을 같이 돌리면 **이번 세션 전체**가 한꺼번에 라이브에 들어간다:
7챕터 39개 재생성 · 메인 b퀘스트 9개 신설 · 마을 어보 4개 · 심해 사이드 7개 +
심해어 NPC 5명 · 저레벨 S 하향 · 난이도 전면 재부여. **되돌리기 어렵다.**
마인팜만 올릴 생각이었으면 아래 「B안」을 쓸 것.

---

## 0. 백업 (필수)

파이프라인은 로컬 `.pre-*` 백업만 남긴다. 원격 백업을 먼저 확보한다.

```bash
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 \
  '~/mcserver/scripts/offsite-backup.sh'      # BlockShip 폴더 전체 → Object Storage
```

접속자도 확인한다 — `deploy-blockship.sh`는 **즉시 재시작**이다.

```bash
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 '~/mcserver/scripts/rcon.py list'
```

---

## 1. 자바 패치 — ★순서 고정 ① → ③

```bash
cd ~/development/blockship-plugin
for P in quest-difficulty-and-tracking minefarm-quest-line; do
  git apply --check ~/barkan-fishing-server/ops/patches/$P.patch \
    && git apply    ~/barkan-fishing-server/ops/patches/$P.patch \
    && echo "✓ $P" || { echo "✗ $P — 충돌, 중단"; break; }
done
./gradlew build
```

③은 ①이 적용된 트리에서 뜬 diff다. 순서를 바꾸면 `QuestManager`·`QuestGui`에서 충돌한다.
충돌하면 `git apply -3`을 먼저 시도할 것.
적용 후 [`ops/patches/README.md`](patches/README.md) 표를 **적용 완료로 고칠 것**(두 번 적용 방지).

## 2. 데이터 파이프라인

**네 JSON이 한 디렉터리에 있는 곳**(dev의 `plugins/BlockShip/`)에서 번호 순서대로.
각 스크립트는 자체 검증에 실패하면 종료한다 — **한 번이라도 ✗가 뜨면 거기서 멈출 것.**

```bash
cd "<dev의 plugins/BlockShip>"
for S in fix_waterfall_cave_refs fix_desert_thread add_leila_side fix_story_polish \
         fix_story_gaps fix_desc_goal_sync drop_blackscale_line fix_canyon_setting \
         fix_forbidden_book seed_ash_vessel spread_side_difficulty fix_dialogue_blackscale \
         fix_dialogue_tone fix_grade_gates build_ch7_quests build_ch7_side \
         spread_main_difficulty add_village_capstones add_minefarm_line add_quest_difficulty; do
  echo "── $S"
  python3 ~/barkan-fishing-server/fish-tools/$S.py || { echo "✗ $S 에서 중단"; break; }
done
```

**B안 — 마인팜만:** 19·20번 둘만 돌린다(`add_minefarm_line` → `add_quest_difficulty`).
20번은 전 퀘스트 난이도를 다시 계산하므로 **항상 마지막에 한 번**은 돌아야 한다.

## 3. dev 검증

```bash
~/deploy-dev.sh          # 빌드 → dev plugins/ → dev-mc.sh restart
```

인게임에서 최소 이것만 확인:

| 확인 | 방법 |
|---|---|
| 부팅 정상 | 로그에 `NoClassDefFoundError`·`[Crop] CraftEngine 미탑재` 없음 |
| 경작지 카운트 | 섬에서 밭 갈고 10초 뒤 `/퀘스트`에 `섬 경작지 n/32` 오름 |
| 수확 | 특수 밀 수확 → `harvest` 진행도 오름 |
| 제출 | 특수 밀 6개 들고 오스발트 → 인벤에서 실제로 회수됨 |
| 꾸러미 | 압축 꾸러미 들고 **상자 우클릭 → 상자가 열려야 함**(안 풀림) / 웅크림+우클릭 → 풀림 |
| 티켓 | 자심권 500·플라이권 우클릭 사용 |
| 렉 | 밭 갈면서 `/tps` — 20 유지 |

## 4. prod 배포

```bash
~/deploy-blockship.sh    # 빌드 → SCP → systemctl restart (즉시)
```

JSON은 이게 안 올린다. 파이프라인을 돈 JSON을 따로 올린 뒤 리로드:

```bash
scp -i ~/.ssh/oracle-mc.key \
  quests.json npc.json dialogue.json fish.json titles.json \
  ubuntu@168.107.8.107:~/mcserver/plugins/BlockShip/
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 \
  '~/mcserver/scripts/rcon.py "데이터리로드" && ~/mcserver/scripts/rcon.py "npc동기화"'
```

> ★`deploy-blockship.sh`/`stage-blockship.sh`의 실제 동작은 스크립트 본문으로 확인할 것 —
> 이 문서는 CLAUDE.md 기재 내용을 옮긴 것이고, JSON 업로드 경로는 스크립트에 없다.

**무인 기간이면** `~/stage-blockship.sh`를 쓴다 — 06:00 KST 데일리 유지보수 때 자동 적용되고
구 jar이 `backups/deployed-jars/`에 백업된다(롤백용).

## 5. 롤백

```bash
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 '~/mcserver/scripts/rollback-jar.sh list'
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 '~/mcserver/scripts/rollback-jar.sh yes'
```

JSON은 0번에서 뜬 오프사이트 백업에서 `oci os object get`으로 되돌린다.
★`rollback-jar.sh`는 하이픈 없이 쓴다(모바일 키보드가 `--`를 대시로 바꾼 실측 사례).
