# 3층 — 폰에서 prod 까지 (당겨오는 배포)

맥 없이, 폰에 SSH 키 없이 배포가 도는 파이프라인. **방향이 핵심이다** — 밀어넣지
않고 오라클이 당겨온다. 리소스팩이 이미 이 구조다(Release URL 을 server.properties 가 가리킴).

```
폰(클라우드 세션)  코드 수정 → git push
       ↓
GitHub Actions     빌드 → 부팅 스모크(1층) → 통과 시에만 Release 발행
       ↓                                      ※수동 promote 일 때만
오라클 cron        fetch-staging.sh (*/5) → 검증 → ~/mcserver/staging/
       ↓
mcdev-up.sh --jar  (2층) 폰 마크 클라로 실제 확인          ← 여기가 dev 테스트 자리
       ↓
       ├─ 마커 없음 → 06:00  nightly-restart.sh 적용 + 구 jar 백업 + 데일리 리포트
       └─ APPLY_NOW → 즉시   nightly-restart.sh --now (예고 후 재시작 + 부팅확인)
```

## 즉시 배포 (APPLY_NOW)

06:00 을 기다리지 않는 길. **22번 포트가 막혀 있어** 클라우드 세션에서 prod 로 밀어넣는
건 원천 불가능하다 — 그래서 당겨오는 이 구조에 마커 한 줄만 얹었다.

Actions 를 `apply_now=true` 로 수동 실행하면 Release 본문에 `APPLY_NOW` 가 박히고,
`fetch-staging.sh` 가 그것을 보면 staging 배치 직후 `nightly-restart.sh --now` 를
`exec` 한다(cron 의 flock 이 재시작·부팅확인 끝까지 유지돼 다음 주기가 안 겹친다).

**적용 로직은 복제하지 않았다.** validate-staged 게이트·리소스팩 교차검증·구 jar 백업이
전부 `nightly-restart.sh` 에 있고, 사본을 만들면 한쪽만 고쳐지는 날이 온다. 즉시 모드가
정기와 다른 점은 넷뿐이다:

| | 정기 06:00 | 즉시 (--now) |
|---|---|---|
| staging 이 비면 | 그래도 재시작(누수 정리) | **재시작 안 함** |
| 예고 | restart-warning.sh 가 30/10/5/1분 전 | `GRACE` 초(기본 60) 방송 후 |
| 알림 | 🌅 데일리 리포트 + `.backup-status` 소비 | 🚀 배포 알림, **status 파일 안 건드림** |
| 부팅 확인 | 안 함(프리즈 워치독이 8분 내 잡음) | RCON 40회×5초, 실패 시 롤백법 안내 |

★`APPLY_NOW` 는 문자열 매칭이다. 워크플로 release notes 문구를 다듬다 그 낱말을 지우면
즉시 배포가 **에러 없이** 06:00 배포로 되돌아간다.

## 모바일 리소스팩 배포

리소스팩은 BlockShip jar와 별도 흐름이다. 폰에서 GitHub 저장소의
**Actions → Mobile production resource pack → Run workflow**를 열고 다음처럼 실행한다.

| 입력 | 동작 |
|---|---|
| `promote=false` | 빌드·구조검증만 하고 Release를 만들지 않음 |
| `promote=true`, `apply_now=false` | `MOBILE_RP_PROMOTE` Release 발행, prod가 설정만 갱신하고 다음 재시작 때 적용 |
| `promote=true`, `apply_now=true` | `MOBILE_RP_PROMOTE` + `APPLY_NOW` Release 발행, prod가 최대 5분 안에 예고 후 재시작 |

prod의 `fetch-resourcepack.sh`가 cron(`*/5`)으로 Release를 당겨온다. 본문에
`MOBILE_RP_PROMOTE`가 있고 `barkan-resourcepack.zip` 자산이 있는 Release만 대상이며,
일반 Release·`latest`·dev 업로드는 무시한다. 따라서 폰에 SSH 키를 넣을 필요가 없다.

오라클 최초 설치:

```bash
cp fetch-resourcepack.sh ~/mcserver/scripts/
cp resourcepack-restart.sh ~/mcserver/scripts/
chmod +x ~/mcserver/scripts/fetch-resourcepack.sh ~/mcserver/scripts/resourcepack-restart.sh
~/mcserver/scripts/fetch-resourcepack.sh --dry-run
( crontab -l 2>/dev/null | grep -v 'fetch-resourcepack.sh' || true; \
  echo '*/5 * * * * flock -n ~/mcserver/.fetch-rp.lock ~/mcserver/scripts/fetch-resourcepack.sh >> ~/mcserver/backups/ops.log 2>&1' ) | crontab -
```

`apply_now=true`는 접속자에게 60초 예고 후 전체 재시작한다. 적용 전 공개 URL의 SHA1,
ZIP 무결성, `pack.mcmeta`, `assets/barkan/`을 다시 검사하고, 부팅 뒤 RCON까지 확인한다.

## 승격 게이트 — 이 전제를 깨지 말 것

Actions 는 **수동 promote 일 때만** Release 를 만든다. 그래서
`fetch-staging.sh` 는 "최신 Release 가 있다 = 사람이 승격을 눌렀다" 로 믿는다.

**push 마다 Release 가 생기게 바꾸면 이 전제가 깨진다.** `nightly-restart.sh` 는
staging 에 있는 걸 무조건 적용하므로, 그 순간부터 오타 하나가 다음날 06:00 에
라이브로 간다.

## 설치 (오라클에서 한 번)

```bash
cp fetch-staging.sh ~/mcserver/scripts/ && chmod +x ~/mcserver/scripts/fetch-staging.sh

# GitHub 토큰 — fine-grained PAT, 대상 repo 에 contents:read 만
printf '%s' 'github_pat_...' > ~/mcserver/.github-token
chmod 600 ~/mcserver/.github-token

# 기본 repo = wsi1212/blockship-plugin (2026-08-14 실측 확인, private).
# 다른 repo 를 쓸 때만 BLOCKSHIP_REPO 로 덮어쓴다.
~/mcserver/scripts/fetch-staging.sh --dry-run

# cron — */5 다. 즉시 배포의 실제 지연이 이 주기이고, 변화가 없으면 로그를 안 남기므로
#        */15 에서 조여도 ops.log 노이즈가 늘지 않는다.
( crontab -l 2>/dev/null; \
  echo '*/5 * * * * flock -n ~/mcserver/.fetch.lock ~/mcserver/scripts/fetch-staging.sh' ) | crontab -

# 즉시 배포를 쓰려면 nightly-restart.sh 도 최신이어야 한다(--now 모드가 거기 있다)
cp ../nightly-restart.sh ~/mcserver/scripts/ && chmod +x ~/mcserver/scripts/nightly-restart.sh
PREVIEW=1 NOW=1 ~/mcserver/scripts/nightly-restart.sh   # 즉시 모드 메시지 미리보기
```

## 안전장치

| 위험 | 막는 방법 |
|---|---|
| 깨진 다운로드가 06:00에 그대로 적용됨 | 크기 일치 + zip 무결성 + **루트에 plugin.yml 존재**까지 검증 후에만 배치 |
| 미검증 jar 자동 배포 | Release 발행 자체가 수동 승격 (1층 스모크 통과 전제) |
| 같은 걸 15분마다 다시 받음 | 태그를 상태 파일에 기록, 변화 없으면 **조용히** 종료 (알림 노이즈 없음) |
| staging 에 jar 가 여러 개 | 배치 전 기존 `BlockShip-*.jar` 제거 |
| 디스크 압박 | 88% 이상이면 배치 중단 (disk-guard 는 92%에서 백업을 지운다) |
| **`plugins/` 루트 오염** | 이 스크립트는 **staging 까지만** 쓴다. 루트에는 절대 쓰지 않는다 |

## 훈련소 기간 — 배포 동결

폰이 없는 몇 주 동안은 jar 를 흘려보내지 않는다. 깨지면 사람 손이 필요한데
그 손이 없다.

```bash
# 나가기 전
rm -f ~/mcserver/staging/BlockShip-*.jar          # staging 비우기
crontab -l | grep -v fetch-staging | crontab -    # fetch cron 해제
```

컨텐츠(JSON)만 바꿀 거면 `/데이터리로드` 경로라 재시작이 없으니 상대적으로 안전하다.
자리 잡은 뒤 cron 을 다시 걸면 된다.

## 실측 검증 (2026-08-13)

`validate_jar` 를 6개 케이스로 확인:

| 입력 | 판정 |
|---|---|
| 루트에 `plugin.yml` | 통과 ✓ |
| 루트에 `paper-plugin.yml` | 통과 ✓ |
| 하위폴더에만 `plugin.yml` (Bukkit 이 못 읽음) | 거부 ✓ |
| yml 없는 jar | 거부 ✓ |
| 손상된 zip | 거부 ✓ |
| 빈 파일 | 거부 ✓ |

**돌려보니 나온 버그**: 처음엔 `unzip -l` 로 검사했는데 그 출력은 크기·날짜가 앞에
붙은 표 형식이라 `(^|/)plugin\.yml` 경계에 안 걸렸다. → **정상 jar 를 전부 거부**해서
staging 에 아무것도 안 올라가는 상태였다. 이름만 한 줄씩 내는 `unzip -Z1` 로 교체.

GitHub API 호출 구간은 실제 private repo·토큰이 없어 미검증 — **첫 실행은 반드시
`--dry-run`** 으로 repo 이름과 토큰 권한을 확인할 것.

## 남은 확인 항목

- [ ] `BLOCKSHIP_REPO` 실제 repo 이름 (기본값이 맞는지)
- [ ] PAT 는 fine-grained, 해당 repo 에 **contents:read 만**. 넓게 주지 말 것
- [ ] `nightly-restart.sh` 가 staging 에서 jar 를 집는 파일명 패턴이
      `BlockShip-*.jar` 와 맞는지 (다르면 `ASSET_GLOB` 조정)
