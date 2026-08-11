# 바르칸 통계 웹 대시보드 (statsweb)

stats-system-plan.md §10-5·§10-6 구현체. FastAPI 단일 프로세스, Discord OAuth2 로그인.
①~⑩ 페이지는 순수 통계 열람(쓰기 엔드포인트 0개). ⑪ 콘솔(Phase 6)만 admin 역할 전용 쓰기
액션(RCON 경유 kick/ban/pardon/whitelist/say/list) — CSRF+확인다이얼로그+audit_log 기록.
stats-lab/queries.py를 웹·CLI가 공유한다.

## 로컬 개발 실행 (Mac)

```bash
cd statsweb
python3 -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env        # 아래 채우기
cp admins.json.example admins.json   # 본인 Discord ID로 교체
../stats-lab/pull.sh         # 또는 dev 서버의 telemetry/ 폴더를 직접 STATSLAB_DATA_DIR로 지정
venv/bin/uvicorn app:app --reload --port 8080
```

`.env`의 `STATSLAB_DATA_DIR`을 비워두면 `stats-lab/data/`(pull.sh가 받아온 사본)를 쓴다. dev
서버로 바로 테스트하려면 `STATSLAB_DATA_DIR=/Users/.../plugins/BlockShip/telemetry`처럼 dev
telemetry 폴더를 직접 가리키면 된다.

## 샌드박스 (Discord 로그인 없이 전체 UI 확인)

```bash
python3 ../stats-lab/seed_sandbox.py   # 가짜 데이터 생성(선택 — run_sandbox.sh가 없으면 자동으로 함)
./run_sandbox.sh                       # http://127.0.0.1:8090, role=admin 세션 자동 주입
```
`RCON_PASSWORD`를 절대 채우지 않은 채로 뜬다(`rcon_client.RconDisabled`) — 콘솔 액션 폼을
눌러봐도 실제 서버엔 아무 명령도 안 나가고 "RCON 비활성" 실패로만 audit_log에 기록된다.

## Phase 6(⑪ 콘솔) 관련 추가 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `RCON_HOST` | `127.0.0.1` | statsweb과 같은 박스의 RCON — 절대 외부 노출 금지 |
| `RCON_PORT` | `25575` | |
| `RCON_PASSWORD` | (빈 문자열=비활성) | **prod에 실제 값을 넣는 순간부터 콘솔 액션이 진짜 서버에 명령을 보낸다** — server.properties의 `rcon.password`와 동일 값 |
| `PLAYERDATA_DIR` | (빈 문자열=뷰어 비활성) | `/playerdata` 조회 대상 — prod는 `~/mcserver/plugins/BlockShip/playerdata` |
| `BANNED_PLAYERS_FILE` | (빈 문자열=뷰어 비활성) | `/banlist` 대상 — prod는 `~/mcserver/banned-players.json` |

`requirements.txt`에 `python-multipart`가 새로 추가됨(콘솔 액션 폼 파싱에 필요) — **기존
prod venv에 재설치 필요**: `venv/bin/pip install -r requirements.txt`.

## 운영자 1회 작업 체크리스트 (Phase 5 배치분 — 전부 완료)

- [x] barkan.kro.kr A레코드 → 168.107.8.107
- [x] Discord Developer Portal 앱 생성 + redirect 등록 + client id/secret
- [x] `.env` 기입 + admins.json 어드민 등록
- [x] Caddyfile 블록 추가 + systemd `statsweb.service` 설치

## 검증 상태 (2026-07-28 갱신)

- **Phase 5(①~⑩)**: prod 실배치 완료(barkan.kro.kr/admin, Discord 실로그인 확인). HTTPS 인증서
  발급 완료(kro.kr 레이트리밋 해제 후 원복 확인).
- **Phase 6(⑪ 콘솔, RCON 액션 카탈로그+playerdata/밴목록 뷰어+audit_log)**: 코드 완성 + 샌드박스에서
  역할게이팅(viewer 403·admin 통과)/CSRF 불일치 거부/audit_log 기록/admin.action 이벤트 미러까지
  전부 실동작 확인. **prod 미배포** — 배포 시 위 표의 `RCON_PASSWORD`를 실제로 채우는 순간부터
  진짜 서버에 명령이 나가므로 별도 명시 요청 시에만, 신중하게 진행할 것.
- C10(강화 단계별 몇강 집계)은 ⑧ RNG 페이지 세 번째 섹션으로 병합, prod 배포 시 자동 포함.
