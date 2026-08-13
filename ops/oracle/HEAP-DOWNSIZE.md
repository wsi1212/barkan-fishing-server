# 비상 힙 축소 — 2 OCPU / 12 GB 로 강제될 때

Always Free A1 한도가 **2 OCPU / 12 GB** 로 내려갔다(현재 prod 는 4/24).
오라클이 한도 초과 인스턴스를 정지시키면 12GB 로 리사이즈해야 하는데,
**현재 16G 힙은 12GB 박스에 물리적으로 안 들어간다.**

급할 때 처음 계산하지 말고 이 문서대로 적용한다.

## 실측 (2026-08-13, 컨테이너)

Paper 1.21.10 + Aikar 소용량 플래그 + `-Xms8G -Xmx8G -XX:+AlwaysPreTouch`:

| 항목 | 값 |
|---|---|
| 부팅 | ✅ 41초 |
| JVM RSS | **8.56 GB** |
| 힙 외 오버헤드 | **0.56 GB** |
| OOM·GC 경고 | 0건 |

★**이 0.56GB 는 바닥값이다** — 플러그인 0개, 슈퍼플랫, 접속자 0명 기준.

## prod 실측 (2026-08-13) — 이게 진짜 숫자다

```
$ free -m
              total    used    free   shared  buff/cache   available
Mem:          23974   18523     489      102        5382        5451
```

힙이 16G(16384MB)인데 `used` 가 18523MB → **힙 밖으로 2,139MB** 를 쓰고 있다
(JVM 오버헤드 + OS + 기타 프로세스 전부 포함).

컨테이너 실측 0.56GB 와 4배 차이 나는 이유는 **플러그인이 20개**라서다:

```
AIBuilder · Axiom · BarkanChess · BarkanWorldWarp · BetterHud · BetterModel
BlockShip · Chunky · Citizens · CoreProtect · CraftEngine · Geyser · floodgate
GrimAC · ProtocolLib · ViaVersion · ViaBackwards · VotifierPlus
multiverse-core · worldedit
```

메타스페이스·Netty 다이렉트 버퍼·리전 파일 캐시가 그만큼 늘어난다.

### 그래서 권장 힙 (실측 2,139MB 오버헤드 기준)

12GB = 12,288MB. 여기서 오버헤드 2,139MB 를 빼고, 월드 IO 용 page cache 를 남긴다.

| 힙 | 힙+오버헤드 | 남는 page cache | 판단 |
|---|---|---|---|
| 9G | 11,355 MB | ~0.9 GB | ✗ 너무 얇다, IO 가 죽는다 |
| 8G | 10,331 MB | ~1.9 GB | 가능하지만 월드 IO 가 답답해진다 |
| **7G** | 9,307 MB | ~2.9 GB | **권장** |
| 6G | 8,283 MB | ~3.9 GB | 보수적, 인구 늘면 부족할 수 있음 |

참고로 현재 prod 의 `buff/cache` 가 5,382MB 다 — 8개 월드를 굴리는 데 그만큼 쓰고 있다.
12GB 로 내려가면 이 여유가 크게 줄어드니 **page cache 를 최대한 남기는 쪽**이 맞다.

**7G 로 시작**하고 `/tps`·GC 로그를 보며 조정한다.

## ★★ 놓치기 쉬운 함정: Aikar 플래그는 12GB 경계에서 값이 다르다

CLAUDE.md 에 *"Java 힙 16G — 2026-07-07 12G→16G, Aikar ≥12G 대용량 힙 플래그"* 라고
적혀 있다. 즉 현재 `start.sh` 는 **대용량 변형**을 쓰고 있다.

**`-Xmx` 만 8G 로 바꾸고 대용량 플래그를 그대로 두면 GC 설정이 힙 크기와 안 맞는다.**
아래 5개 값을 반드시 함께 되돌린다.

| 플래그 | 현재 (start.sh 실측) | **8G 이하로 내릴 때** |
|---|---|---|
| `G1NewSizePercent` | 40 | **30** |
| `G1MaxNewSizePercent` | 50 | **40** |
| `G1HeapRegionSize` | 16M | **8M** |
| `G1ReservePercent` | 15 | **20** |
| `InitiatingHeapOccupancyPercent` | 20 | **15** |

나머지 플래그(`+UseG1GC` `+ParallelRefProcEnabled` `MaxGCPauseMillis=200`
`+UnlockExperimentalVMOptions` `+DisableExplicitGC` `+AlwaysPreTouch`
`G1HeapWastePercent=5` `G1MixedGCCountTarget=4` `G1MixedGCLiveThresholdPercent=90`
`G1RSetUpdatingPauseTimePercent=5` `SurvivorRatio=32` `+PerfDisableSharedMem`
`MaxTenuringThreshold=1`)는 두 변형이 동일하므로 그대로 둔다.

### ✅ 2026-08-13 `start.sh` 실측 — 위 "현재" 열이 정확히 일치한다

```
-Xms16G -Xmx16G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200
-XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch
-XX:G1NewSizePercent=40 -XX:G1MaxNewSizePercent=50 -XX:G1HeapRegionSize=16M
-XX:G1ReservePercent=15 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4
-XX:InitiatingHeapOccupancyPercent=20 -XX:G1MixedGCLiveThresholdPercent=90
-XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32
-XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1
```

다섯 개 값(40 / 50 / 16M / 15 / 20)이 모두 대용량 변형이다. 추정이 아니라 확인된 사실이니
힙을 내릴 때 **반드시 함께 되돌린다.**

## 실측 검증된 전체 명령

이 조합으로 부팅·정상 종료를 확인했다(위 실측). `8G` 를 `7G` 로 바꿔 쓰면 된다:

```bash
java -Xms7G -Xmx7G \
  -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 \
  -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch \
  -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M \
  -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 \
  -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 \
  -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 \
  -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 \
  -jar paper-1.21.10.jar --nogui
```

`-Xms` 와 `-Xmx` 를 같게 두는 이유: `+AlwaysPreTouch` 와 함께 쓰면 힙을 처음에
전부 커밋해서 런타임 중 확장으로 인한 렉을 없앤다(현재 prod 방식과 동일).

## CPU 도 반토막이다 (2 OCPU)

메모리만 문제가 아니다. 4 → 2 OCPU 로 줄어든다.
Paper 의 메인 틱은 대체로 단일 스레드라 체감이 절반이 되는 건 아니지만,
청크 생성·IO 풀·Moonrise 워커가 코어를 쓴다. 베타 인구면 버티겠지만
`view-distance`·`simulation-distance` 를 한 단계 낮출 준비를 해두는 게 좋다.

## 부수 효과 — 2층(같은 박스 dev)은 불가능해진다

12GB 에 7G 힙이면 `MemAvailable` 이 3~4GB 다. `mcdev-up.sh` 의 문턱이 3500MB 이므로
**dev 시작이 거부된다.** 설계대로 동작하는 것이다(prod 를 OOM 으로 죽이는 것보다
dev 를 못 켜는 게 낫다).

그 시나리오에서는 **도쿄/오사카 무료 2/12 계정을 dev 로** 쓰는 게 합리적이 된다.
dev 는 핑이 상관없다. `mcdev-sync.sh` 의 rsync 를 SSH 경유로 바꾸고
(`rsync -e ssh ubuntu@prod:~/mcserver/plugins/ ...`) 메모리 가드와
`prod_running` 확인을 제거하면 그대로 쓸 수 있다.

## 아직 검증 못 한 것

- [x] ~~`start.sh` 의 현재 플래그~~ — 2026-08-13 실측 확인, 표와 일치
- [x] ~~실제 플러그인 물린 상태의 오버헤드~~ — prod `free -m` 으로 2,139MB 확인
- [ ] **7G 에서 실플레이가 버티는지** — 접속해서 `/tps` 와 GC 로그 확인 필요.
      리사이즈가 강제되기 전에 미리 해볼 수는 없다(24GB 에서 7G 로 낮춰 돌려보면
      page cache 가 넉넉해 조건이 다르다). 그래도 GC 압박은 미리 볼 수 있다
- [ ] ⚠️ **디스크 48GB / 여유 23GB** — `df -h /` 실측. 2층 dev 가 월드를 복사하면
      빠듯하다. `mcdev-sync.sh` 는 80% 에서 거부하지만, 애초에 `--no-worlds` 나
      월드 일부만 쓰는 게 현실적이다. 월드 크기 확인: `du -sh ~/mcserver/world*`
