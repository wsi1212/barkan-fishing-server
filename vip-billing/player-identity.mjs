// 마크 플레이어 식별자 검증.
//
// ★베드락(Geyser/Floodgate) 유저도 통과해야 한다. 이걸 빼 놓으면 베드락 유저는 게임에서
//   /디스코드 를 쳤을 때 코드 발급부터 400(invalid_player)으로 막혀 디스코드 인증을
//   아예 못 한다(2026-09-07 확인 — prod 에 이미 베드락 계정이 3개 있었다).
//
// 이름: 서버 안에서 진짜 이름은 Floodgate 접두사가 붙은 쪽이다. prod 접두사는 "." 이고
//       실측값은 .wsi1212 / .SiltyBiscuit669 / .FlyIncheon 처럼 접두사 + 자바 규칙이다.
//       접두사는 Floodgate 설정값이라 운영자가 바꾸면 여기도 같이 바꿔야 한다.
// UUID: Floodgate 는 new UUID(0, xuid) 를 준다 → 상위 64비트가 전부 0이라 RFC-4122 의
//       버전(3번째 그룹 [1-5])·변종(4번째 그룹 [89ab]) 니블이 그 자리에 없다.
//       실측: 00000000-0000-0000-0009-01f758e05895
//       그래서 버전·변종을 강제하지 않는다. SQL/URL 안전성은 16진수+하이픈 고정폭이 지킨다.
//
// ★이 규칙은 2026-09-05 에 prod /srv/vip-billing/server.mjs 에 손으로 적용된 핫픽스를
//   그대로 옮겨 온 것이다(레포에는 안 들어와 있었다). 여기 있는 이유는 다음 vip-billing
//   배포가 그 핫픽스를 조용히 되돌리지 않게 하려는 것 — 문구를 되돌리지 말 것.

const JAVA_NAME = /^[A-Za-z0-9_]{3,16}$/;
const FLOODGATE_NAME = /^\.[A-Za-z0-9_]{3,16}$/;   // 접두사 "." = Floodgate username-prefix
const ANY_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const FLOODGATE_UUID = /^0{8}-0{4}-0{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const minecraftName = (value) =>
  typeof value === "string" && (JAVA_NAME.test(value) || FLOODGATE_NAME.test(value));

export const validUuid = (value) => typeof value === "string" && ANY_UUID.test(value);

/** 베드락(Floodgate) 계정인지. 디스코드 봇의 에디션 표시 역할과 같은 판정이다. */
export const isBedrockUuid = (value) => typeof value === "string" && FLOODGATE_UUID.test(value.trim());
