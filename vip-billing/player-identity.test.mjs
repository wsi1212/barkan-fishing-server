// node --test player-identity.test.mjs
// 베드락(Floodgate) 계정이 검증에서 튕기면 그 유저는 디스코드 인증을 아예 못 한다.
// 아래 UUID·이름은 prod playerdata 에서 그대로 가져온 실측값이다.
import { test } from "node:test";
import assert from "node:assert/strict";
import { isBedrockUuid, minecraftName, validUuid } from "./player-identity.mjs";

const BEDROCK = [
  ["00000000-0000-0000-0009-01f758e05895", ".wsi1212"],
  ["00000000-0000-0000-0009-01f8ea20af18", ".SiltyBiscuit669"],
  ["00000000-0000-0000-0009-01fab2441535", ".FlyIncheon"],
];

test("베드락 실측 계정이 UUID·이름 검증을 통과한다", () => {
  for (const [uuid, name] of BEDROCK) {
    assert.ok(validUuid(uuid), `uuid ${uuid}`);
    assert.ok(minecraftName(name), `name ${name}`);
    assert.ok(isBedrockUuid(uuid), `bedrock ${uuid}`);
  }
});

test("자바 계정은 그대로 통과하고 베드락으로 오인되지 않는다", () => {
  const uuid = "b8f4e5a2-1c3d-4e6f-8a9b-0c1d2e3f4a5b";
  assert.ok(validUuid(uuid));
  assert.ok(minecraftName("wsi1212"));
  assert.equal(isBedrockUuid(uuid), false);
});

test("망가진 값은 여전히 거른다", () => {
  assert.equal(validUuid("not-a-uuid"), false);
  assert.equal(validUuid("00000000-0000-0000-0009-01f758e0589"), false);  // 12자리 미달
  assert.equal(validUuid("00000000-0000-0000-0009-01f758e05895x"), false);
  assert.equal(validUuid(null), false);
  assert.equal(minecraftName("ab"), false);                 // 3자 미만
  assert.equal(minecraftName("a".repeat(17)), false);       // 16자 초과
  assert.equal(minecraftName(".."), false);
  assert.equal(minecraftName(".ab"), false);                // 접두사 뒤 본체가 3자 미만
  assert.equal(minecraftName("..wsi1212"), false);          // 접두사 중복
  assert.equal(minecraftName("wsi.1212"), false);           // 접두사는 맨 앞에만
  assert.equal(minecraftName("Silty Biscuit"), false);      // 공백
});
