import { test } from "node:test";
import assert from "node:assert/strict";
import { MEMBERSHIP_ROLES, applyMembershipRole, ensureMembershipRoles } from "./membership-roles.mjs";

console.log = () => {};
console.warn = () => {};

function fakeGuild(names = []) {
  const roles = new Map(names.map((name, index) => [`existing_${index}`, { id: `existing_${index}`, name }]));
  const created = [];
  let next = 0;
  return {
    created,
    roles: {
      cache: roles,
      fetch: async id => (id === undefined ? roles : roles.get(id) ?? null),
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
    guild,
    log,
    roles: {
      cache,
      add: async id => { cache.add(id); log.added.push(id); },
      remove: async id => { cache.delete(id); log.removed.push(id); },
    },
  };
}

const roleNames = Object.values(MEMBERSHIP_ROLES).map(role => role.name);

test("기존 멤버십 역할은 이름으로 재사용한다", async () => {
  const guild = fakeGuild(roleNames);
  const ids = new Map();
  await ensureMembershipRoles(guild, ids);
  assert.deepEqual(guild.created, []);
  assert.deepEqual([...ids.entries()], [
    ["VIP", "existing_0"], ["MVP", "existing_1"], ["MVP_PLUS", "existing_2"],
  ]);
});

test("역할이 없으면 권한 없는 표시 역할 세 개를 만든다", async () => {
  const guild = fakeGuild();
  await ensureMembershipRoles(guild, new Map());
  assert.deepEqual(guild.created.map(role => role.name), roleNames);
  assert.deepEqual(guild.created.map(role => role.permissions), [[], [], []]);
});

test("등급 변경 시 이전 역할을 회수하고 새 역할 하나만 준다", async () => {
  const guild = fakeGuild(roleNames);
  const ids = new Map([["VIP", "existing_0"], ["MVP", "existing_1"], ["MVP_PLUS", "existing_2"]]);
  const member = fakeMember(guild, ["existing_0"]);
  const result = await applyMembershipRole(member, "MVP_PLUS", ids);
  assert.equal(result.changed, true);
  assert.deepEqual(member.log.removed, ["existing_0"]);
  assert.deepEqual(member.log.added, ["existing_2"]);
});

test("이미 맞는 등급은 건드리지 않는다", async () => {
  const guild = fakeGuild(roleNames);
  const ids = new Map([["VIP", "existing_0"], ["MVP", "existing_1"], ["MVP_PLUS", "existing_2"]]);
  const member = fakeMember(guild, ["existing_1"]);
  const result = await applyMembershipRole(member, "MVP", ids);
  assert.equal(result.changed, false);
  assert.deepEqual(member.log, { added: [], removed: [] });
});

test("만료 또는 잘못된 등급이면 모든 멤버십 역할을 회수한다", async () => {
  const guild = fakeGuild(roleNames);
  const ids = new Map([["VIP", "existing_0"], ["MVP", "existing_1"], ["MVP_PLUS", "existing_2"]]);
  const member = fakeMember(guild, ["existing_0", "existing_2", "verified"]);
  const result = await applyMembershipRole(member, null, ids);
  assert.equal(result.tier, null);
  assert.deepEqual(member.log.removed, ["existing_0", "existing_2"]);
  assert.deepEqual(member.log.added, []);
  assert.equal(member.roles.cache.has("verified"), true);
});
