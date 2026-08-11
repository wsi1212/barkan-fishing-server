# 바르칸 열도 VIP 결제 백엔드

Oracle의 Minecraft 서버와 분리해 운영하는 결제 전용 서비스다. PostgreSQL을 구독의 단일 권위로 사용하며, 게임 계정 연결·구독 조회·자동갱신 취소·환불 요청·관리자 환불 승인·토스 단건 결제 연동을 제공한다.

공개 주소: `https://barkan.kro.kr/vip/`  
상태 확인: `https://barkan.kro.kr/vip/health`

## 배포 구성

- 서비스: `/srv/vip-billing`, Linux 사용자 `vipbilling`, `127.0.0.1:3100`
- DB: PostgreSQL `vip_billing` / `vip_billing` 역할. 로컬 루프백만 사용.
- 공개 프록시: 기존 Caddy의 `/vip/*` 경로. 별도 포트를 열지 않는다.
- 비밀값: `/etc/vip-billing/vip-billing.env` (권한 600). Git 및 플러그인 데이터에 넣지 않는다.

## 운영 흐름

1. 게임 안 `/구독`은 일회용 연결 코드를 백엔드에 만들고, 플레이어는 `/vip/link`에서 코드를 입력한다.
2. 결제 성공 페이지는 토스 서버 승인 응답과 주문 UUID·금액을 함께 검증한 뒤에만 30일을 연장한다.
3. 자동갱신 취소는 이미 결제한 기간을 보존한다. 현재는 단건 30일권이므로 상태만 기록하며, 빌링 도입 시 다음 청구 방지에 사용한다.
4. 환불은 플레이어 요청 → `/vip/admin`의 운영자 승인 → 토스 전액 취소 → 즉시 이용권 종료 순서다.

## 최초 운영 셋업

`/etc/vip-billing/vip-billing.env`에 `INTERNAL_API_TOKEN`, `ADMIN_PASSWORD`, 토스 계약 후 `TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY`를 넣고 `sudo systemctl restart vip-billing`을 실행한다. 토스 키가 비어 있으면 결제 버튼은 안전하게 비활성 페이지를 보인다.

초기 관리자 비밀번호는 Oracle에만 생성되어 있다. 서버에서 다음 명령으로 확인한다. 출력은 공유하거나 채팅에 남기지 않는다.

```bash
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 \
  'sudo sed -n -E "/^(ADMIN_USERNAME|ADMIN_PASSWORD)=/p" /etc/vip-billing/vip-billing.env'
```

토스 키를 넣은 뒤에는 다음 두 상태가 모두 `active`인지 확인한다.

```bash
ssh -i ~/.ssh/oracle-mc.key ubuntu@168.107.8.107 \
  'sudo systemctl restart vip-billing && systemctl is-active vip-billing && systemctl is-active mcserver'
```

토스 개발자센터에는 아래 주소를 등록한다.

- 성공 URL: `https://barkan.kro.kr/vip/payment/success`
- 실패 URL: `https://barkan.kro.kr/vip/payment/fail`
- 웹훅 URL: `https://barkan.kro.kr/vip/webhooks/toss`

웹훅은 결제 권한을 직접 부여하지 않는다. 성공 페이지에서 주문 ID·금액과 토스 승인 결과를 서버 간에 검증한 뒤에만 이용권을 연장한다. 웹훅은 취소 상태와 원본 이벤트 원장 보존에 사용한다.

## 게임 운영 명령

- 플레이어: `/구독` → 웹 계정 연결 코드 발급
- OP: `/구독 <닉네임>` → 기본 VIP 30일 지급
- OP: `/구독 <닉네임> <MVP|VIP|MVP+> <일수>` → 원하는 등급과 기간 지급

활성 구독자는 채팅에서 기존 칭호 앞에 멤버십 태그가 붙는다. 예: `§6[VIP]§e[백전노장] §fwsi1212§7: §fasd`.
