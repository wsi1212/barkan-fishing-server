# prod 이전 런북 — 친구 계정 → 본인 계정

> ## 🚨 상태: 전제 붕괴 (2026-08-13) — 이 이전은 실행할 수 없다
>
> **오라클 공식 문서 원문:**
> > "You can create OCI Ampere A1 Compute instances in any availability domain,
> > **except South Korea North (Chuncheon)**."
>
> **춘천에서는 A1을 만들 수 없다.** 가입 드롭다운에 한국이 없는 게 원인이 아니고,
> 오라클이 춘천을 A1에서 명시적으로 배제한 것이다. 새 계정을 몇 개 만들어도 안 된다.
>
> **게다가 Always Free A1 한도가 반토막 났다:**
>
> | | 이전 | 현재 (문서 확인) |
> |---|---|---|
> | A1 | 4 OCPU / 24 GB | **2 OCPU / 12 GB** |
> | 월 시간 | 3,000 / 18,000 | **1,500 OCPU-h / 9,000 GB-h** |
>
> 즉 새 계정으로 얻을 수 있는 최선은 **도쿄/오사카의 2 OCPU / 12 GB** 다.
> 현재 prod(춘천 4/24)보다 핑도 사양도 나쁘다. **옮길 이유가 없어졌다.**
>
> ### ★★ 절대 규칙: 그 인스턴스를 terminate 하지 마라
>
> 춘천은 A1 제외이고, 한도 초과 shape 는 재생성이 막힌다
> (*"If an existing resource is terminated, it may not be possible to recreate
> resources above the updated Always Free limit."*).
> **현재 prod 는 더 이상 발급되지 않는 물건이다.**
> stop(정지)은 되돌릴 수 있지만 terminate(종료)는 영구다.
> 아래 7단계의 "옛 박스 정리" 를 그대로 따라가면 복구 불가능한 것을 날린다.
>
> ### 대신 할 일
>
> 1. 친구에게 **콘솔 Announcements + 계정 이메일 확인** 요청 (한도 통지 여부)
> 2. **예산 알림 $1** 설정 — 미터가 돌기 시작하면 즉시 감지
> 3. **IAM 관리자 계정** 확보 — 이제 편의가 아니라 감시를 위한 필수
> 4. **8G 힙 축소 대비 검증** — 강제로 2/12 가 되면 16G 힙은 불가능하다.
>    급할 때 처음 해보지 말고 미리 확인
> 5. PAYG 전환 검토 — 4/24 유지 보도가 있으나 지원팀 답변이 모순되니
>    문의 후 **답변을 기록으로 남길 것**
>
> ※ 시행 시점은 불명확하다. 공식 이메일 공지가 없었고, 콘솔과 문서가 어긋난다는
> 보도가 있다. 검색 요약에 "8월 18일" 이 스쳤으나 1차 출처에서 확인하지 못했다 —
> 날짜를 사실로 취급하지 말 것. 시점 불명확 자체가 지금 대비하는 이유다.
>
> ※ 부수 효과: prod 가 12GB 로 내려가면 **2층(같은 박스 dev)은 불가능**해진다.
> `mcdev-up.sh` 의 메모리 가드가 정확히 그걸 막는다(설계대로). 그 시나리오에서는
> 오사카 무료 2/12 를 dev 로 쓰는 게 합리적이 된다 — dev 는 핑이 상관없다.
>
> **아래 0~7단계는 한국 A1 이 다시 열리는 날에만 유효하다.** 그때까지는 참고 자료다.
>
> 출처: [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
> · [InfoQ](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
> · [TerminalBytes](https://terminalbytes.com/oracle-cloud-free-tier-changes-2026/)

**타이밍 자체는 지금이 가장 싸다.** 출시 전이라 유저 재등록 공지가 필요 없고,
서버 목록에 IP를 박아둔 사람도 사실상 없다. 출시 후에 하면 그 비용이 유저 이탈로
돌아온다. 그래서 리전이 열리면 **미루지 말고** 하는 게 맞다.

**원칙: 새 박스가 완전히 검증될 때까지 옛 박스를 절대 건드리지 않는다.**
롤백은 "DNS를 되돌리는 것"이고, 그게 가능한 건 옛 박스가 살아있을 때뿐이다.

---

## 0단계 — 계정 만들기 (폰 브라우저로 가능)

### ★★ 2026-08-13 실측: 무료 가입에 한국 리전이 없다

가입 화면의 홈 영역 드롭다운 ASIA-PACIFIC 목록을 끝까지 확인한 결과:

```
Australia East (Sydney) · Australia Southeast (Melbourne)
India South (Hyderabad) · India West (Mumbai) · Indonesia North (Batam)
Japan Central (Osaka) · Japan East (Tokyo) · Malaysia West 2 (Kulai)
Singapore (Singapore) · Singapore West (Singapore)          ← 여기서 끝
```

**South Korea Central (Seoul) / South Korea North (Chuncheon) 둘 다 없다.**
무료 계층 신규 가입에는 현재 한국이 열려 있지 않다.

그리고 같은 화면에 오라클이 이렇게 적어놨다:

> 각 지역의 가용성은 **시간에 따라 변경될 수 있음**에 유의하십시오.
> **지역을 변경하기 위해 여러 계정을 생성하려고 시도하지 마십시오.**

### 그래서 나온 결론 — 무료 가입을 지금 쓰지 않는다

홈 리전은 영구적이고, 여러 계정을 만드는 건 금지돼 있다. 즉 **무료 가입은
사실상 일회성 자원**이고 그 값어치는 "한국이 열리는 날 한국에 계정을 만들 수 있는
권리"다. 지금 오사카에 써버리면 그 옵션이 사라진다.

**dev 박스 하나 얻으려고 그 옵션을 태우는 건 손해다.** dev는 기존 박스의
`~/mcdev/`(2층)로 이미 해결돼 있다.

### 핑이 소유권보다 중요하다

| 리전 | 한국에서 핑 |
|---|---|
| 춘천 (현재 prod) | **5~10ms** |
| 도쿄 | 30~40ms |
| 싱가포르 | 70~90ms |

이 서버의 강점이 "한국 핑 5~10ms"이고, 게임의 핵심이 **타이밍 기반 낚시 미니게임**이다.
prod를 도쿄로 옮기는 건 유저가 체감하는 퇴보다. **한국에 못 만들면 prod는 옮기지 않는다.**

### 그럼 오늘 할 수 있는 것 — IAM 관리자

친구에게 기존 테넌시의 **IAM 관리자 계정**을 하나 만들어달라고 한다
(Identity → Users → 생성 → Administrators 그룹). 그러면 인스턴스·백업 버킷·
동적그룹·방화벽·API 키를 **당신이 직접** 관리한다. 부탁은 한 번뿐이다.

한계: 소유권은 여전히 친구 것이다(계정 폐쇄·결제·복구 불가). 하지만 **문제의 운영
쪽 절반은 오늘 해결**되고, 이전 작업 자체도 당신 손으로 하게 된다.

### 자기 테넌시를 정말 원하면 — PAYG 경로

같은 가입 화면이 직접 안내한다: *"무료 계층에서 제공되지 않는 특정 데이터 지역에
액세스해야 하는 경우 오라클 영업 팀에 문의하여 **사용량 기준 계정에 등록하는 것을
고려**"*. 즉 **Pay As You Go 가입에는 한국이 열려 있을 수 있다.**

- A1 **4 OCPU / 24GB 는 Always Free 한도**라 PAYG 계정에서도 요금이 $0 이다
- ★단 카드가 걸리므로 **OCI 예산 알림을 $1~5 로 설정**할 것. 블록스토리지·이그레스가
  한도를 넘으면 청구가 시작되는데, 군 복무 중에는 청구서를 못 본다
- 유휴 회수 대상에서도 빠진다(무인 운영에 유리)

### 아니면 기다린다

가용성은 시간에 따라 변한다. **가입 화면의 드롭다운을 주기적으로 확인**하면 된다
(로그인 불필요, 30초). 입대 전에 한 번 더 보고, 열려 있으면 그때 잡는다.

### 명의

**본인 명의로 만든다.** 남의 이름으로 무료 계정을 쌓는 건 ToS 위반이고 그게
계정 정지 사유다. 지금 prod가 남의 계정에 있는 게 문제인 것과 같은 이유로,
새 계정도 본인 것이어야 의미가 있다.

### Always Free 상한 — 이걸 넘기면 트라이얼 후 정지된다

| 자원 | 상한 (테넌시 합계) |
|---|---|
| A1.Flex (ARM) | **4 OCPU / 24 GB** |
| 블록 스토리지 | 200 GB |

신규 계정은 30일 트라이얼 크레딧이 붙는다. 그동안은 상한을 넘겨도 돌아가지만
트라이얼이 끝나면 **초과분이 정지·회수된다.** 그러니 처음부터 **정확히 4/24** 로
띄운다. 지금 박스와 같은 사양이라 이전도 그대로 맞는다.

### PAYG 업그레이드를 진지하게 고려할 것

카드를 등록해 Pay As You Go 로 올려도 **Always Free 한도 내에서는 계속 $0** 이다.
그런데 두 가지가 달라진다고 알려져 있다:

- **유휴 회수 대상에서 빠진다** — Always Free 인스턴스는 유휴 상태가 길면
  오라클이 회수할 수 있다. 군 복무 중 접속이 거의 없는 서버가 정확히 그 프로필이다.
- **용량 확보가 쉬워진다** — A1 자리 경쟁에서 유리하다는 보고가 많다.

★정확한 회수 정책은 가입 시점 약관으로 직접 확인할 것. 다만 무인 운영을 전제하면
카드 하나 걸어두는 게 서버 하나 잃는 것보다 싸다.

---

## 1단계 — 용량 사냥

춘천 A1 자리는 귀하다. 기존 박스도 재시도 루프를 오래 돌려 4/24 를 얻었다.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/oracle-new -C mc-prod     # 새 키 (기존 키 재사용 금지)
# OCI 콘솔에서 API 키 등록 → ~/.oci/config 설정
launch-retry.sh --discover     # 필요한 OCID 를 찾아준다
launch-retry.sh --dry-run      # 사양이 Always Free 상한 내인지 확인
launch-retry.sh                # 사냥 시작 (성공 시 Discord 알림)
```

콘솔에서 손으로 **Create Instance** 를 눌러보는 것도 먼저 해볼 만하다 —
그 순간 자리가 있으면 스크립트 없이 바로 된다.

★사냥 루프는 **항상 켜진 기계**에서 돌려야 한다. 며칠~몇 주 걸릴 수 있다.
현재 상황에서는 맥이나 기존 오라클 박스 중 하나다.

---

## 2단계 — 새 박스 기반 세우기

```bash
sudo apt update && sudo apt install -y tmux rsync unzip python3 curl
# Java — 기존과 동일하게 Azul Zulu 21 ARM
#   (기존: /usr/lib/jvm/zulu21-ca-arm64)
```

방화벽 **2계층 모두** 열어야 외부에서 닿는다:

| 포트 | 용도 | OCI Security List | iptables |
|---|---|---|---|
| 22 | SSH | ✅ | ✅ |
| 25565 | 마크 | ✅ | ✅ |
| 80 / 443 / 3000 | 기타 서비스 | ✅ | ✅ |
| 25566 | dev (2층) | 선택 | 선택 |
| **25575** | RCON | ❌ **넣지 말 것** | ❌ 기본 REJECT 유지 |

RCON 은 localhost 전용이어야 한다. 외부에 열면 콘솔 권한이 그대로 새 나간다.

---

## 3단계 — 데이터 이전

옛 박스에서 새 박스로 직접 rsync 하는 게 가장 빠르다(둘 다 춘천).

```bash
# 옛 박스에서 실행. 먼저 저장 플러시.
~/mcserver/scripts/rcon.py save-all flush
sleep 10
rsync -avz -e "ssh -i ~/.ssh/oracle-new" \
  --exclude 'session.lock' --exclude 'logs/' --exclude 'cache/' \
  ~/mcserver/ ubuntu@<새IP>:~/mcserver/
```

### 옮겨야 하는 것 — 체크리스트

- [ ] 월드 전부 — `world` `world_nether` `world_the_end` `guild_world`
      `island_world` `afk_world` `flatroom` `mine`
- [ ] `plugins/` 전체 — ★`Citizens/saves.yml`(NPC 157명), `BlockShip/`(퀘스트·어종·
      지역 JSON + **playerdata**), ProtocolLib, ViaVersion/ViaBackwards 5.11.0
- [ ] `server.properties` — 리소스팩 URL·SHA1 포함. **RCON 비밀번호는 새로 발급**
- [ ] `ops.json` · `whitelist.json` · `banned-*.json`
- [ ] Paper jar (`paper-1.21.11.jar`)
- [ ] `start.sh` — ★힙 결정: 16G 유지할지, dev(2층)를 같은 박스에서 쓸 거면 12G
- [ ] `scripts/` 전부 + **cron 전체**
- [ ] `staging/` · `backups/` (백업은 새로 시작해도 되지만 롤백용 구 jar 는 챙길 것)

### 잊기 쉬운 비밀·설정

- [ ] `scripts/discord-webhook.url`
- [ ] `scripts/heartbeat.sh` 안의 healthchecks.io URL
- [ ] `.github-token` (3층 fetch용)
- [ ] `~/.ssh/` 안의 키들 (백업·동기화용으로 쓰던 것)

---

## 4단계 — ★오프사이트 백업 재구축 (제일 잘 잊는 곳)

`offsite-backup.sh` 는 **instance principal** 로 인증한다 — 박스에 OCI 키가 없고,
대신 인스턴스 자체가 신원이다. 그래서 **테넌시가 바뀌면 통째로 다시 세워야 한다.**
안 하면 백업이 **조용히** 멈추고, 그걸 몇 달 뒤에 알게 된다.

- [ ] 새 테넌시에 버킷 `mc-backups` 생성 + **버전관리 ON**
- [ ] 동적 그룹 `mc-instance-dg` 생성 — 매칭룰의 **인스턴스 OCID 를 새 것으로**
      (CLAUDE.md 경고: "인스턴스 재생성 시 OCID 바뀜 → 매칭룰도 갱신 필요")
- [ ] 정책 생성 — 동적 그룹에 해당 버킷 object 관리 권한
- [ ] `offsite-backup.sh` 를 **손으로 한 번 돌려서** 실제로 올라가는지 확인
- [ ] `oci os object list` 로 올라간 객체 확인

---

## 5단계 — 검증 (전환 전에)

새 박스는 **DNS 를 바꾸지 않은 상태**에서 IP 직접 접속으로 검증한다.

- [ ] 서버 부팅 — `Done (` 도달, BlockShip **enable** 확인
- [ ] 치명 예외 0건 (`NoClassDefFoundError` 등) — 1층 스모크 기준과 동일
- [ ] 폰 마크 클라로 **IP 직접 접속** — 로그인, 리소스팩 적용, 스킨
- [ ] 내 계정 데이터가 맞나 — 레벨·돈·장비·강화·칭호 (playerdata 이전 확인)
- [ ] NPC 157명 표시 + 우클릭 대화 + 퀘스트 수락
- [ ] 낚시 → 미니게임 → 판매 → 아이스박스
- [ ] 페리·포탈·잠긴문 — ★`Worlds.dimKey` 경로. 크로스월드 TP가 조용히 실패하는지
- [ ] `rcon.py list` 응답
- [ ] `watchdog.sh` 수동 실행 → 정상 판정
- [ ] `nightly-restart.sh` **`PREVIEW=1`** 로 리포트 미리보기 (발송·재시작 없음)
- [ ] `local-backup.sh` 1회 + `offsite-backup.sh` 1회 성공
- [ ] `disk-guard.sh` · `crash-watch.py` 수동 1회
- [ ] 디스코드 알림이 실제로 도착하나

---

## 6단계 — 전환 (다운타임 0)

★예약 IP `168.107.8.107` 은 **테넌시를 넘어갈 수 없다.** 새 IP가 된다.
그래서 도메인이 있는 게 중요하다 — 이미 `barkan.kro.kr` → 옛 IP 로 붙어 있다.

```
1. (며칠 전) TTL 을 300초 이하로 내린다   ★TTL 변경도 옛 TTL 만료 후 퍼진다
2. 새 박스 검증 완료
3. A 레코드를 새 IP 로 변경
4. ★옛 박스를 계속 켜둔다 — TTL 의 2~3배 동안
5. 새 박스 로그로만 접속이 들어오는 걸 확인
6. 그때 옛 박스 정지 (삭제는 며칠 더 뒤)
```

4번이 다운타임을 0으로 만든다. 캐시가 남은 유저는 옛 박스로, 갱신된 유저는 새
박스로 들어가고, 둘 다 살아있으므로 아무도 실패하지 않는다.

**단, 그 구간에는 두 박스에 각자 플레이가 쌓인다.** 출시 전이라 사실상 본인뿐이니
문제가 안 되지만, 유저가 있는 상태라면 옛 박스를 화이트리스트로 잠그거나
점검 공지를 내고 짧게 끊는 게 데이터 분기를 막는 정직한 방법이다.

- [ ] 전환 후 새 IP 를 디스코드에 공지 (도메인이 죽었을 때의 뒷문)
- [ ] `kro.kr` **갱신 주기 확인** — 무료 서비스는 주기적 재확인을 요구할 수 있고,
      갱신을 놓치면 서버는 멀쩡한데 이름이 안 풀린다. 훈련소 기간에 걸리면
      치명적이니, 수동 갱신이고 주기가 짧으면 유료 도메인 + 자동갱신을 검토

---

## 7단계 — 정리

- [ ] 옛 박스: 며칠 관찰 후 정지 → 문제 없으면 친구에게 반납 또는 dev 로 강등
- [ ] dev 를 옛 박스에 둘 거면 `mcdev-sync.sh` 의 rsync 를 SSH 경유로 바꾼다
      (`rsync -e ssh ubuntu@prod:~/mcserver/plugins/ ...`), 메모리 가드와
      `prod_running` 확인은 제거
- [ ] CLAUDE.md 갱신 — IP, OCID, 테넌시, 예약IP OCID, 동적그룹
- [ ] `resize-retry.sh` 등 옛 테넌시용 자동화 정리

---

## 롤백

전환 후 문제가 생기면 **A 레코드를 옛 IP 로 되돌린다.** 옛 박스가 켜져 있는
동안은 이게 몇 분 안에 되는 완전한 롤백이다. 그래서 6단계에서 옛 박스를 성급히
지우지 않는 게 중요하다.
