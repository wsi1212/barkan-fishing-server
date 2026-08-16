// node --test guild-sync.test.mjs
// 실제 디스코드를 때리지 않는 부분(역할 계획 계산, 카테고리 배치, 이름 정규화)만 검증한다.
import { test } from "node:test";
import assert from "node:assert/strict";
import { ChannelType } from "discord.js";
import {
  CATEGORY_CHANNEL_LIMIT, GUILD_ROLE_PREFIX, SERVER_CHANNEL_LIMIT,
  pickCategory, planMemberSync, provisionGuild, safeFileName, textChannelName,
} from "./guild-sync.mjs";

const RANKS = new Map([["MASTER", "r_master"], ["VICE_MASTER", "r_vice"], ["OFFICER", "r_officer"], ["MEMBER", "r_member"]]);
const GUILD_A = "g_A";
const GUILD_B = "g_B";
const ALL_GUILD_ROLES = new Set([GUILD_A, GUILD_B]);

const plan = (targets, holders) => planMemberSync({
  guildRoleId: GUILD_A, rankRoleIds: RANKS, targets,
  holders: new Map(holders), allGuildRoleIds: ALL_GUILD_ROLES,
});

test("새 길드원은 길드 역할과 직책 역할을 함께 받는다", () => {
  const result = plan([{ discordId: "u1", rank: "MASTER" }], [["u1", []]]);
  assert.deepEqual(result, [{ discordId: "u1", add: [GUILD_A, "r_master"], remove: [] }]);
});

test("직책이 바뀌면 이전 직책만 회수한다", () => {
  const result = plan([{ discordId: "u1", rank: "VICE_MASTER" }], [["u1", [GUILD_A, "r_member"]]]);
  assert.deepEqual(result, [{ discordId: "u1", add: ["r_vice"], remove: ["r_member"] }]);
});

test("이미 맞는 사람은 건드리지 않는다", () => {
  const result = plan([{ discordId: "u1", rank: "MASTER" }], [["u1", [GUILD_A, "r_master"]]]);
  assert.deepEqual(result, []);
});

test("탈퇴자는 길드 역할과 직책을 모두 잃는다", () => {
  const result = plan([], [["u1", [GUILD_A, "r_member", "verified"]]]);
  assert.deepEqual(result, [{ discordId: "u1", add: [], remove: [GUILD_A, "r_member"] }]);
});

test("다른 길드로 옮긴 사람은 이 길드 역할만 잃고 직책은 유지한다", () => {
  // 옮겨간 길드의 작업이 먼저 돌아 이미 새 직책을 줬을 수 있다. 여기서 회수하면 그걸 지운다.
  const result = plan([], [["u1", [GUILD_A, GUILD_B, "r_master"]]]);
  assert.deepEqual(result, [{ discordId: "u1", add: [], remove: [GUILD_A] }]);
});

test("인증 역할 같은 무관한 역할은 절대 건드리지 않는다", () => {
  const result = plan([{ discordId: "u1", rank: "MEMBER" }], [["u1", ["verified", "booster"]]]);
  assert.deepEqual(result[0].remove, []);
  assert.deepEqual(result[0].add, [GUILD_A, "r_member"]);
});

test("디스코드 서버에 없는 길드원은 건너뛴다", () => {
  const result = plan([{ discordId: "ghost", rank: "MEMBER" }], []);
  assert.deepEqual(result, []);
});

test("디스코드 미연동(discordId 없음)은 계획에 들어가지 않는다", () => {
  const result = plan([{ discordId: null, rank: "MEMBER" }], []);
  assert.deepEqual(result, []);
});

// ===== 카테고리 배치 =====

function fakeGuild(channels, { onCreate } = {}) {
  const cache = new Map(channels.map(c => [c.id, c]));
  return {
    roles: { everyone: { id: "everyone" } },
    channels: {
      cache,
      create: async options => {
        onCreate?.(options);
        const created = { id: `new_${cache.size}`, name: options.name, type: options.type, parentId: options.parent ?? null };
        cache.set(created.id, created);
        return created;
      },
    },
  };
}
const category = (id, n) => ({ id, name: `길드 ${n}`, type: ChannelType.GuildCategory, parentId: null });
const child = (id, parentId) => ({ id, name: `c${id}`, type: ChannelType.GuildText, parentId });

test("자리가 있는 기존 카테고리를 재사용한다", async () => {
  const guild = fakeGuild([category("cat1", 1), child("a", "cat1"), child("b", "cat1")]);
  const picked = await pickCategory(guild, "길드");
  assert.equal(picked.id, "cat1");
});

test("카테고리가 꽉 차면 다음 번호로 새로 만든다", async () => {
  const full = [category("cat1", 1)];
  for (let i = 0; i < CATEGORY_CHANNEL_LIMIT - 1; i += 1) full.push(child(`f${i}`, "cat1"));
  let createdName = null;
  const guild = fakeGuild(full, { onCreate: options => { createdName = options.name; } });
  const picked = await pickCategory(guild, "길드");
  assert.equal(createdName, "길드 2", "채널 2개가 안 들어가면 새 카테고리를 파야 한다");
  assert.equal(picked.name, "길드 2");
});

test("번호가 10을 넘어도 사전순이 아니라 숫자순으로 고른다", async () => {
  const channels = [category("cat9", 9), category("cat10", 10)];
  for (let i = 0; i < CATEGORY_CHANNEL_LIMIT; i += 1) channels.push(child(`x${i}`, "cat9"));
  const guild = fakeGuild(channels);
  const picked = await pickCategory(guild, "길드");
  assert.equal(picked.id, "cat10", "길드 9 가 꽉 찼으면 길드 10 으로 가야 한다");
});

test("서버 채널 상한에 닿으면 조용히 넘어가지 않고 실패한다", async () => {
  const channels = [];
  for (let i = 0; i < SERVER_CHANNEL_LIMIT; i += 1) channels.push(child(`x${i}`, null));
  const guild = fakeGuild(channels);
  await assert.rejects(() => pickCategory(guild, "길드"), /channel_limit_reached/);
});

test("다른 이름의 카테고리는 길드 풀로 쓰지 않는다", async () => {
  const guild = fakeGuild([{ id: "other", name: "공지", type: ChannelType.GuildCategory, parentId: null }]);
  const picked = await pickCategory(guild, "길드");
  assert.equal(picked.name, "길드 1");
});

// ===== 재시도 멱등성 =====
// 2026-08-17 배포 사고: 멤버 동기화가 레이트리밋으로 실패하면 작업 전체가 실패로 보고되는데,
// 그 전에 만든 역할·채널 id 가 저장돼 있지 않아 재시도마다 새로 찍어냈다(러지 길드가 5벌).

function fakeGuildFull({ roles = [], channels = [] } = {}) {
  const roleCache = new Map(roles.map(r => [r.id, r]));
  const chanCache = new Map(channels.map(c => [c.id, c]));
  const created = { roles: 0, channels: 0 };
  return {
    created,
    roles: {
      everyone: { id: "everyone" },
      cache: roleCache,
      fetch: async id => roleCache.get(id) ?? null,
      create: async options => {
        created.roles += 1;
        const r = { id: `role_${roleCache.size}`, name: options.name };
        roleCache.set(r.id, r); return r;
      },
    },
    channels: {
      cache: chanCache,
      fetch: async id => chanCache.get(id) ?? null,
      create: async options => {
        created.channels += 1;
        const c = {
          id: `chan_${chanCache.size}`, name: options.name, type: options.type,
          parentId: options.parent ?? null,
          permissionOverwrites: { cache: new Map((options.permissionOverwrites ?? []).map(o => [o.id, o])) },
        };
        chanCache.set(c.id, c); return c;
      },
    },
  };
}
const ownedChannel = (id, type, roleId, parentId) => ({
  id, name: id, type, parentId,
  permissionOverwrites: { cache: new Map([[roleId, {}], ["everyone", {}]]) },
});

test("저장된 id 가 없어도 같은 이름의 역할을 재사용한다", async () => {
  const guild = fakeGuildFull({
    roles: [{ id: "existing_role", name: `${GUILD_ROLE_PREFIX}러지` }],
    channels: [
      category("cat1", 1),
      ownedChannel("t1", ChannelType.GuildText, "existing_role", "cat1"),
      ownedChannel("v1", ChannelType.GuildVoice, "existing_role", "cat1"),
    ],
  });
  const result = await provisionGuild(guild, "러지", null, "길드");
  assert.equal(guild.created.roles, 0, "역할을 새로 만들면 안 된다");
  assert.equal(guild.created.channels, 0, "채널을 새로 만들면 안 된다");
  assert.deepEqual(result, { roleId: "existing_role", categoryId: "cat1", textChannelId: "t1", voiceChannelId: "v1" });
});

test("역할만 남고 채널이 지워졌으면 채널만 다시 만든다", async () => {
  const guild = fakeGuildFull({
    roles: [{ id: "existing_role", name: `${GUILD_ROLE_PREFIX}러지` }],
    channels: [category("cat1", 1)],
  });
  const result = await provisionGuild(guild, "러지", null, "길드");
  assert.equal(guild.created.roles, 0);
  assert.equal(guild.created.channels, 2, "텍스트·음성 둘만");
  assert.equal(result.roleId, "existing_role");
});

test("아무것도 없으면 역할 1개 + 채널 2개만 만든다", async () => {
  const guild = fakeGuildFull({ channels: [category("cat1", 1)] });
  await provisionGuild(guild, "새길드", null, "길드");
  assert.equal(guild.created.roles, 1);
  assert.equal(guild.created.channels, 2);
});

// ===== 이름 정규화 =====

test("채널 이름은 소문자·하이픈으로 정규화하고 한글은 유지한다", () => {
  assert.equal(textChannelName("기모띠"), "기모띠");
  assert.equal(textChannelName("Deep Sea"), "deep-sea");
  assert.equal(textChannelName("바르칸 #1!"), "바르칸-1");
});

test("이름이 전부 걸러지면 빈 이름 대신 대체값을 쓴다", () => {
  assert.equal(textChannelName("###"), "guild");
  assert.equal(safeFileName("../../etc/passwd"), "______etc_passwd");
});

test("길드 역할 접두어는 다른 역할과 겹치지 않을 만큼 특이하다", () => {
  assert.ok(GUILD_ROLE_PREFIX.startsWith("["));
});
