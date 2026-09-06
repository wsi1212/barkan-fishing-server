// node --test edition-roles.test.mjs
// 디스코드를 때리지 않고 역할 판정·부여/회수만 검증한다. guild/member 는 가짜다.
import { test } from "node:test";
import assert from "node:assert/strict";
import { EDITION_ROLES, applyEditionRole, editionOf } from "./edition-roles.mjs";

// ensureEditionRoles 의 생성 로그가 테스트 출력을 덮지 않게 한다.
console.log = () => {};
console.warn = () => {};

const BEDROCK_UUID = "00000000-0000-0000-0009-01f758e05895";  // prod 실측
const JAVA_UUID = "b8f4e5a2-1c3d-4e6f-8a9b-0c1d2e3f4a5b";

function fakeGuild(names = []) {
  const roles = new Map(names.map((name, i) => [`existing_${i}`, { id: `existing_${i}`, name }]));
  const created = [];
  let next = 0;
  return {
    created,
    roles: {
      cache: roles,
      fetch: async id => (id === undefined ? roles : roles.get(id) ?? null),   // 인자 없으면 전체 새로고침
      create: async spec => {
        const role = { id: `made_${next++}`, name: spec.name };
        roles.set(role.id, role);
        created.push(spec);
        return role;
      },
    },
  };
}

function fakeMember(guild, held = []) {
  const cache = new Set(held);
  const log = { added: [], removed: [] };
  return {
    guild, log,
    roles: {
      cache,
      add: async id => { cache.add(id); log.added.push(id); },
      remove: async id => { cache.delete(id); log.removed.push(id); },
    },
  };
}

test("Floodgate UUID 는 베드락, 나머지는 자바", () => {
  assert.equal(editionOf(BEDROCK_UUID), "bedrock");
  assert.equal(editionOf("00000000-0000-0000-0009-01fab2441535"), "bedrock");
  assert.equal(editionOf(JAVA_UUID), "java");
  assert.equal(editionOf(null), "java");   // 알 수 없으면 자바 — 베드락을 잘못 주장하지 않는다
});

test("역할이 없으면 만들고 해당 에디션만 준다", async () => {
  const guild = fakeGuild();
  const member = fakeMember(guild);
  const result = await applyEditionRole(member, BEDROCK_UUID, new Map());
  assert.equal(result.edition, "bedrock");
  assert.equal(result.changed, true);
  assert.deepEqual(guild.created.map(r => r.name), [EDITION_ROLES.java.name, EDITION_ROLES.bedrock.name]);
  assert.deepEqual(guild.created.map(r => r.permissions), [[], []]);   // 권한 없는 표시용
  // 단색 `color` 는 discord.js 14.22+ 에서 deprecated — `colors.primaryColor` 로 준다.
  assert.deepEqual(guild.created.map(r => Object.hasOwn(r, "color")), [false, false]);
  assert.equal(typeof guild.created[0].colors.primaryColor, "number");
  assert.equal(member.log.added.length, 1);
  assert.equal(member.log.removed.length, 0);
});

test("같은 이름의 역할이 이미 있으면 재사용한다", async () => {
  const guild = fakeGuild([EDITION_ROLES.java.name, EDITION_ROLES.bedrock.name]);
  const ids = new Map();
  await applyEditionRole(fakeMember(guild), JAVA_UUID, ids);
  assert.deepEqual(guild.created, []);
  assert.deepEqual([...ids.entries()], [["java", "existing_0"], ["bedrock", "existing_1"]]);
});

test("에디션이 바뀌면 반대쪽을 회수한다", async () => {
  const guild = fakeGuild([EDITION_ROLES.java.name, EDITION_ROLES.bedrock.name]);
  const ids = new Map([["java", "existing_0"], ["bedrock", "existing_1"]]);
  const member = fakeMember(guild, ["existing_1"]);   // 베드락을 들고 있던 사람
  const result = await applyEditionRole(member, JAVA_UUID, ids);
  assert.equal(result.changed, true);
  assert.deepEqual(member.log.added, ["existing_0"]);
  assert.deepEqual(member.log.removed, ["existing_1"]);
});

test("이미 맞는 사람은 건드리지 않는다", async () => {
  const guild = fakeGuild([EDITION_ROLES.java.name, EDITION_ROLES.bedrock.name]);
  const ids = new Map([["java", "existing_0"], ["bedrock", "existing_1"]]);
  const member = fakeMember(guild, ["existing_0"]);
  const result = await applyEditionRole(member, JAVA_UUID, ids);
  assert.equal(result.changed, false);
  assert.deepEqual(member.log, { added: [], removed: [] });
});

test("저장된 id 가 사라졌으면 이름으로 다시 찾는다", async () => {
  const guild = fakeGuild([EDITION_ROLES.java.name, EDITION_ROLES.bedrock.name]);
  const ids = new Map([["java", "gone_1"], ["bedrock", "gone_2"]]);   // 관리자가 지웠다 다시 만든 경우
  await applyEditionRole(fakeMember(guild), JAVA_UUID, ids);
  assert.deepEqual(guild.created, []);   // 중복 생성 금지
  assert.equal(ids.get("java"), "existing_0");
});
