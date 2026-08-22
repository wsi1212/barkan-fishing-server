# 바르칸 열도 VIP 결제 백엔드

Oracle의 Minecraft 서버와 분리해 운영하는 결제 전용 서비스다. PostgreSQL을 구독의 단일 권위로 사용하며, 게임 계정 연결·구독 조회·자동갱신 취소·환불 요청·관리자 환불 승인·계좌이체 주문 확인을 제공한다. 토스 연동 코드는 향후 재개할 수 있도록 `server.mjs`에 주석으로 보존하지만 현재 실행 경로에는 포함하지 않는다.

공개 주소: `https://barkan.kro.kr/vip/`  
상태 확인: `https://barkan.kro.kr/vip/health`

## 배포 구성

- 서비스: `/srv/vip-billing`, Linux 사용자 `vipbilling`, `127.0.0.1:3100`
- DB: PostgreSQL `vip_billing` / `vip_billing` 역할. 로컬 루프백만 사용.
- 공개 프록시: 기존 Caddy의 `/vip/*` 경로. 별도 포트를 열지 않는다.
- 비밀값: `/etc/vip-billing/vip-billing.env` (권한 600). Git 및 플러그인 데이터에 넣지 않는다.

## 운영 흐름

1. 게임 안 `/구독`은 일회용 연결 코드를 백엔드에 만들고, 플레이어는 `/vip/link`에서 코드를 입력한다.
2. 이용 기간은 1·3·5·12개월(각 30·90·150·365일) 중 선택한다. 화면의 기간·금액과 주문의 `period_days`는 `membership-periods.mjs`의 동일한 기준표에서 만든다.
3. 계좌이체 주문 생성 시 선택한 `period_days`를 저장하고, 운영자 입금 확인 시 그 값을 그대로 `extendSubscription`에 전달한다.
4. 자동갱신 취소는 이미 결제한 기간을 보존한다. 환불은 계좌이체 주문 단위로 요청·승인되며, 승인 시 해당 이용권을 종료한다.

### 이용 기간 기준

| 화면 선택 | 주문 `period_days` | 지급 일수 |
| --- | ---: | ---: |
| 1개월 | 30 | 30 |
| 3개월 | 90 | 90 |
| 5개월 | 150 | 150 |
| 12개월 | 365 | 365 |

`orders.period_days`가 결제·입금 확인의 기간 기준이다. 이미 존재하는 주문은 마이그레이션의 기본값 30일을 유지하므로 기존 미완료 주문과 환불 이력을 깨뜨리지 않는다.

## 최초 운영 셋업

`/etc/vip-billing/vip-billing.env`에 `INTERNAL_API_TOKEN`, `ADMIN_PASSWORD`, `BANK_TRANSFER_BANK`, `BANK_TRANSFER_ACCOUNT_NUMBER`, `BANK_TRANSFER_ACCOUNT_HOLDER`를 넣고 `sudo systemctl restart vip-billing`을 실행한다. 계좌 정보가 비어 있으면 주문 생성이 비활성화된다.

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

현재는 토스 개발자센터 URL이나 웹훅을 등록하지 않는다. `/pay/*`, `/payment/success`, `/payment/fail`, `/webhooks/toss`와 토스 환불 코드는 실행되지 않도록 주석 처리되어 있으며, `/health`는 계좌이체 설정 상태를 `paymentConfigured`로 반환한다.

## 게임 운영 명령

- 플레이어: `/구독` → 웹 계정 연결 코드 발급
- OP: `/구독 <닉네임>` → 기본 VIP 30일 지급
- OP: `/구독 <닉네임> <MVP|VIP|MVP+> <일수>` → 원하는 등급과 기간 지급

활성 구독자는 채팅에서 기존 칭호 앞에 멤버십 태그가 붙는다. 예: `§6[VIP]§e[백전노장] §fwsi1212§7: §fasd`.

## 검증 방법

서비스 코드 변경 후 다음을 실행한다.

```bash
cd "/Users/user/Library/Application Support/feather/player-server/servers/07de2d81-991a-47e2-b62d-06c0d1b5150a/plugins/Skript/scripts/vip-billing"
npm test
node --check server.mjs
```

운영과 같은 DB·환경변수로 수동 확인할 때는 각 기간을 한 번씩 선택한다.

1. 결제 화면에서 30·90·150·365일이 표시되는지 확인한다.
2. 계좌이체 주문을 각 기간으로 한 번씩 만든 뒤 운영자 도구의 대기 주문에서 `period_days`가 선택값과 같은지 확인하고, 입금 확인 후 응답 메시지와 구독 만료일을 확인한다.
3. `/pay/*`, `/payment/success`, `/payment/fail`, `/webhooks/toss` 요청이 주문 생성·지급을 일으키지 않는지 확인한다.
4. DB에서 주문과 지급 원장을 대조한다.

```sql
SELECT order_id, payment_method, tier, amount_krw, period_days, status
FROM orders
WHERE minecraft_uuid = '<UUID>'
ORDER BY created_at DESC;

SELECT provider, provider_event_id, status, payload
FROM payment_events
WHERE minecraft_uuid = '<UUID>'
ORDER BY created_at DESC;
```

계좌이체의 입금 확인이 `orders.period_days`와 같은 일수로 `extendSubscription`을 호출하는지 확인한다. 환불 승인도 주문 ID를 기준으로 기존처럼 처리되는지 함께 확인한다.
