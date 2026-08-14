---
name: deploy-prod
description: BlockShip 플러그인 jar 을 클라우드 세션(폰·웹)에서 prod(오라클 춘천)에 배포한다. SSH 없이 GitHub Actions 승격 → 오라클이 당겨오는 경로를 쓴다. "배포해", "prod 에 올려", "즉시 배포", "staging 올려둬", "배포 상태 확인", "롤백해" 같은 요청에 쓴다. 리소스팩 배포(deploy-rp.sh)나 dev(맥) 배포는 이 스킬이 아니다.
---

# prod 배포 — 클라우드 세션에서

## 먼저 알아야 할 제약

**22번 포트 egress 가 원천 차단돼 있다.** prod 도 github.com 도 안 열린다. 하네스가 git
SSH URL 을 HTTPS 로 재작성한다(`url.https://github.com/.insteadOf git@github.com:`).
즉 **SSH 키를 env 로 넣어 줘도 안 된다** — 키 문제가 아니라 구조다. `deploy-blockship.sh`
`stage-blockship.sh` `~/.ssh/oracle-mc.key` 는 전부 맥에만 있다.

뚫리는 건 둘: **GitHub API(MCP 경유)** 와 **HTTPS**. 그래서 배포는 "밀어넣기" 가 아니라
**오라클이 당겨오는** 경로만 가능하다. 확인 명령:

```bash
curl -sS "$HTTPS_PROXY/__agentproxy/status"          # 프록시 상태
timeout 6 bash -c 'cat </dev/null >/dev/tcp/168.107.8.107/22' || echo 막힘
```

셸에서 `api.github.com` 직접 호출도 403 이다("GitHub access is not enabled for this
session"). GitHub 은 **반드시 `mcp__github__*` 도구로** 다룬다.

## 배포 경로

```
클라우드 세션   코드 수정 → 브랜치 push
      ↓
Actions        빌드 → 부팅 스모크(Paper 1.21.11) → 통과 시에만 Release 발행
      ↓                                            ※수동 dispatch 일 때만
오라클 cron    fetch-staging.sh (*/5) → 크기·zip·plugin.yml 검증 → staging/
      ↓
      ├─ APPLY_NOW 마커 없음 → 06:00 KST nightly-restart.sh 가 적용
      └─ APPLY_NOW 마커 있음 → 즉시 nightly-restart.sh --now (예고 후 재시작)
```

## 하는 법

### 1. 지연 배포 (기본, 안전)

staging 에만 올려 두고 06:00 데일리 유지보수가 적용한다.

```
mcp__github__actions_run_trigger
  method: run_workflow · owner: wsi1212 · repo: blockship-plugin
  workflow_id: blockship-smoke.yml
  ref: <브랜치>
  inputs: {"promote": "true"}
```

### 2. 즉시 배포

`apply_now` 를 켠다. Release 본문에 `APPLY_NOW` 가 박히고, 오라클이 당겨오는 순간
적용 + 재시작한다. **최대 지연은 cron 주기(5분)** 다.

```
inputs: {"apply_now": "true"}      # promote 는 자동으로 켜진 것으로 본다
```

접속자가 있으면 `GRACE` 초(기본 60) 예고 후 재시작한다. 재시작 뒤 RCON 으로 부팅까지
확인하고 실패하면 롤백 방법과 함께 Discord 로 알린다.

### 3. 결과 확인

`inputs` 는 boolean 이지만 **문자열 `"true"`/`"false"` 로 넘긴다**(MCP 스키마가 그렇다).

```
mcp__github__actions_list  method: list_workflow_runs · resource_id: blockship-smoke.yml
  workflow_runs_filter: {"event":"workflow_dispatch","branch":"<브랜치>"}  · per_page: 1
mcp__github__actions_get   method: get_workflow_run · resource_id: <run id>
mcp__github__get_latest_release   ← publish 가 실제로 돌았는지는 이걸로 확인
```

`actions_list` 응답은 run 하나당 ~26k 자다. per_page 를 1~2 로 두고, 커서면 파일로
떨어지니 python 으로 슬라이스해 읽는다.

빌드+스모크는 약 2분 30초. 완료 대기는 `sleep` 을 **백그라운드 Bash** 로 띄우고
(포그라운드 sleep 은 막혀 있다) 알림을 받은 뒤 `actions_get` 으로 확인한다.
셸에서 GitHub API 를 폴링하는 Monitor 는 403 이라 조용히 실패한다 — 쓰지 말 것.

## 함정

**★브랜치에서 발행한 Release 는 main 과 갈린다.** 태그의 `target_commitish` 는 `main`
으로 찍히지만 jar 내용물은 그 브랜치다. 이 상태로 두면 **다음에 누가 main 에서 promote
하는 순간 그 변경이 prod 에서 조용히 사라진다.** 인게임 확인이 끝나면 브랜치를 main 에
머지할 것. 머지는 지정 브랜치 밖 push 이므로 사용자 승인 없이는 하지 않는다.

**★"최신 Release 존재 = 사람이 승격을 눌렀다" 는 전제가 파이프라인의 뼈대다.** push
마다 Release 가 생기게 바꾸면 오타 하나가 다음날 라이브로 간다. 워크플로의 `publish`
조건을 건드리지 말 것.

**★APPLY_NOW 는 문자열 매칭이다.** 워크플로의 release notes 문구를 다듬다가 그 낱말을
지우면 즉시 배포가 조용히 06:00 배포로 되돌아간다(에러 없이).

**★jar 만 올리고 재시작을 미루는 중간 상태는 그 자체가 고장이다.** lazy-load
NoClassDefFoundError 로 전방위 부분 고장이 난다(2026-08-03 prod 사고). 이 경로는
적용과 재시작이 한 묶음이라 그 상태가 안 생기지만, 수동으로 끼어들지 말 것.

**★리소스팩과 코드는 별개 배포다.** 글리프(GUI 판)를 새로 구웠으면 리소스팩도 나가야
한다 — 그건 맥에서 `~/deploy-rp.sh` 뿐이다. 코드만 올리면 유저에게 네모가 뜬다.
반대로 팩이 이미 배포돼 있는데 코드가 안 붙은 경우도 있다(2026-08-14 길드 판이 그랬다).
배포된 팩의 실제 내용은 **Release zip** 으로 확인한다 — git 레포는 낡을 수 있다:

```bash
curl -sSL -o rp.zip https://github.com/wsi1212/minecraft-fish-resource-pack/releases/latest/download/barkan-resourcepack.zip
python3 -c "import zipfile,json,io;z=zipfile.ZipFile('rp.zip');g=json.load(io.TextIOWrapper(z.open('assets/barkan/font/gui.json'),encoding='utf-8'));print(len([p for p in g['providers'] if 'guild_' in str(p.get('file',''))]))"
```

## 문제가 생기면

박스에서(맥 SSH 필요):

```bash
~/mcserver/scripts/rollback-jar.sh list      # 후보 + 라이브 sha256 + staging 대기 (무해)
~/mcserver/scripts/rollback-jar.sh yes       # 직전 jar 로 되돌리고 재시작
```

★하이픈 없이 쓴다(모바일 키보드가 `--` 를 대시로 바꾼다 — 스크립트가 정규화한다).
staging 까지 비우므로 다음날 06:00 에 깨진 jar 이 재적용되지 않는다.

클라우드 세션에서 할 수 있는 것은 **더 올리지 않는 것**뿐이다 — 적용 전이면 Release 를
지우는 대신(fetch 가 이미 받았을 수 있다) 사용자에게 `rm ~/mcserver/staging/*.jar` 를
알려 준다.

## 설치 (박스에서 한 번, 맥 SSH 필요)

즉시 배포는 스크립트 두 개가 박스에 최신이어야 동작한다.

```bash
scp -i ~/.ssh/oracle-mc.key ops/oracle/fetch-staging.sh ops/nightly-restart.sh \
    ubuntu@168.107.8.107:~/mcserver/scripts/
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 \
    'chmod +x ~/mcserver/scripts/{fetch-staging,nightly-restart}.sh &&
     ~/mcserver/scripts/fetch-staging.sh --dry-run &&
     PREVIEW=1 NOW=1 ~/mcserver/scripts/nightly-restart.sh'
# cron 을 */15 → */5 로 (즉시 배포의 지연이 이 주기다)
```

★`oracle-ops-scripts/nightly-restart.sh` 는 낡은 사본이다(validate-staged 게이트가
없다). 권위는 `ops/nightly-restart.sh` 다 — 헷갈리지 말 것.
