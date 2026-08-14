# 3층 — 폰에서 prod 까지 (당겨오는 배포)

맥 없이, 폰에 SSH 키 없이 배포가 도는 파이프라인. **방향이 핵심이다** — 밀어넣지
않고 오라클이 당겨온다. 리소스팩이 이미 이 구조다(Release URL 을 server.properties 가 가리킴).

```
폰(클라우드 세션)  코드 수정 → git push
       ↓
GitHub Actions     빌드 → 부팅 스모크(1층) → 통과 시에만 Release 발행
       ↓                                      ※수동 promote 일 때만
오라클 cron        fetch-staging.sh (*/15) → 검증 → ~/mcserver/staging/
       ↓
mcdev-up.sh --jar  (2층) 폰 마크 클라로 실제 확인          ← 여기가 dev 테스트 자리
       ↓
06:00              nightly-restart.sh 가 적용 + 구 jar 백업 + 데일리 리포트
```

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

# cron
( crontab -l 2>/dev/null; \
  echo '*/15 * * * * flock -n ~/mcserver/.fetch.lock ~/mcserver/scripts/fetch-staging.sh' ) | crontab -
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
