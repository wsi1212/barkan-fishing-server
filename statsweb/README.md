# 바르칸 통계 웹 대시보드 (statsweb)

stats-system-plan.md §10-5 구현체. FastAPI 단일 프로세스, Discord OAuth2 로그인, 통계 열람 전용
(쓰기 엔드포인트 0개 — 서버 조작은 인게임 `/통계` 명령만). stats-lab/queries.py를 웹·CLI가
공유한다.

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

## 운영자 1회 작업 체크리스트 (prod 배치 전, §10-5)

이 세션은 코드/설정 템플릿까지만 준비했다 — 아래는 사람이 직접 해야 하는 부분(계정·DNS·비밀값이
필요해 AI가 대신할 수 없음). 전부 끝나야 실제 배치가 가능하다.

- [ ] **barkan.kro.kr A레코드**가 `168.107.8.107`(오라클 예약 IP)을 가리키는지 확인
- [ ] **Discord Developer Portal**(discord.com/developers/applications)에서 새 앱 생성
  - OAuth2 → Redirects에 `https://barkan.kro.kr/admin/callback` 등록
  - Client ID / Client Secret 확보
- [ ] 오라클 박스 `~/mcserver/statsweb/.env`에 위 client id/secret 기입,
  `SESSION_SECRET`은 `python3 -c "import secrets;print(secrets.token_hex(32))"`로 재생성
- [ ] `admins.json`에 어드민 전원의 Discord ID(닉·역할) 기입 — ID는 디스코드 설정→고급→
  개발자 모드 켜고 프로필 우클릭→ID 복사
- [ ] `oracle-ops-scripts/statsweb.service` 설치 + `oracle-ops-scripts/
  caddy-barkan-admin-snippet.txt`를 기존 Caddyfile에 추가(★lh-bizben 블록은 그대로 두고
  추가만) + `systemctl reload caddy`(무중단)

이 저장소(oracle-ops-scripts/ 미러)에는 위 파일들이 준비되어 있지만, **실제 오라클 박스 설치·
systemd 등록·Caddy reload는 prod 인프라 변경**이라 별도 명시 요청이 있을 때만 수행한다.

## 검증 상태 (2026-07-28)

- 세션/인증 가드, 10개 페이지 라우트 전부 로컬(TestClient, forged 세션 쿠키)로 실제 렌더 확인.
- SVG 차트 4종(bar/stacked-bar/line/scatter) 전부 실데이터+합성데이터로 정상 렌더 확인.
- Discord OAuth2는 authorize URL 조립 로직만 검증(실제 토큰 교환·콜백은 진짜 Discord 앱
  credential이 있어야 해서 이 환경에서 왕복 테스트 불가) — 코드 자체는 Discord OAuth2 표준
  플로우를 그대로 구현.
- prod 미배포. 로컬 파일만 존재.
