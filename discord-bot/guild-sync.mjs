import { ChannelType, PermissionsBitField } from "discord.js";
import { mkdir, appendFile } from "node:fs/promises";
import { join } from "node:path";

// 길드 전용 디스코드 채널·역할 동기화.
//
// 설계 전제(중요): 길드 역할과 길드 채널에 권한을 일절 주지 않는다. 길드 채널은 "길드원에게만 보인다"가
// 전부이고, 메시지·채널 관리는 서버 운영자만 한다. 그래서 길드장이 바뀌어도 채널을 건드릴 일이 없고,
// 채널 수정 레이트리밋(채널당 10분 2회)에 걸릴 일도 없다.
//
// 디스코드 상한: 서버당 채널 500개(카테고리 포함) / 카테고리 50개 / 역할 250개. 부스트로 안 올라간다.
// 그래서 길드마다 카테고리를 파지 않고(그러면 50길드에서 막힘) 공용 카테고리 풀에 채널 2개씩만 넣는다.
// 역할도 길드당 1개만 쓰고 직책 표시는 공용 역할 4종을 돌려 쓴다.

export const RANK_ROLE_NAMES = { MASTER: "길드장", VICE_MASTER: "부길드장", OFFICER: "간부", MEMBER: "길드원" };
export const GUILD_ROLE_PREFIX = "[길드] ";
export const CATEGORY_CHANNEL_LIMIT = 48;  // 실제 상한 50, 경합 여유
export const SERVER_CHANNEL_LIMIT = 480;   // 실제 상한 500
const ARCHIVE_MESSAGE_CAP = 200_000;

const TEXT_ALLOW = [
  PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages,
  PermissionsBitField.Flags.ReadMessageHistory, PermissionsBitField.Flags.AttachFiles,
  PermissionsBitField.Flags.EmbedLinks, PermissionsBitField.Flags.AddReactions,
  PermissionsBitField.Flags.UseExternalEmojis,
];
const VOICE_ALLOW = [
  PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.Connect,
  PermissionsBitField.Flags.Speak, PermissionsBitField.Flags.Stream,
  PermissionsBitField.Flags.UseVAD,
];

export function textChannelName(guildId) {
  const cleaned = String(guildId).trim().toLowerCase().replace(/\s+/g, "-").replace(/[^0-9a-z가-힣ㄱ-ㅎㅏ-ㅣ_-]/gu, "");
  return cleaned.slice(0, 90) || "guild";
}
export function safeFileName(guildId) {
  return String(guildId).replace(/[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ_-]/gu, "_").slice(0, 60) || "guild";
}

/**
 * 역할 부여/회수 계획만 계산하는 순수 함수. 디스코드 호출이 없으므로 그대로 테스트할 수 있다.
 *
 * @param guildRoleId   이 길드의 `[길드] 이름` 역할 id
 * @param rankRoleIds   Map(rank -> 공용 직책 역할 id)
 * @param targets       [{discordId, rank}] — 지금 이 길드에 있어야 하는 사람들
 * @param holders       Map(discordId -> 그 사람이 현재 가진 역할 id 배열)
 * @param allGuildRoleIds  서버에 존재하는 모든 `[길드] ` 역할 id 집합
 */
export function planMemberSync({ guildRoleId, rankRoleIds, targets, holders, allGuildRoleIds }) {
  const rankIds = [...rankRoleIds.values()];
  const wanted = new Map(targets.filter(t => t.discordId).map(t => [t.discordId, t.rank]));
  const plan = [];

  for (const [discordId, rank] of wanted) {
    const current = holders.get(discordId);
    if (!current) continue; // 디스코드 서버에 없는 사람. 재입장하면 guildMemberAdd 가 처리한다.
    const has = new Set(current);
    const rankId = rankRoleIds.get(rank);
    const add = [guildRoleId, rankId].filter(id => id && !has.has(id));
    const remove = rankIds.filter(id => id !== rankId && has.has(id));
    if (add.length || remove.length) plan.push({ discordId, add, remove });
  }

  for (const [discordId, current] of holders) {
    if (wanted.has(discordId)) continue;
    const has = new Set(current);
    if (!has.has(guildRoleId)) continue;
    const remove = [guildRoleId];
    // 다른 길드로 옮겨 간 경우 그쪽 작업이 이미 직책을 줬을 수 있다.
    // 남아 있는 길드 역할이 없을 때만 직책까지 회수한다.
    const inAnotherGuild = [...has].some(id => id !== guildRoleId && allGuildRoleIds.has(id));
    if (!inAnotherGuild) remove.push(...rankIds.filter(id => has.has(id)));
    plan.push({ discordId, add: [], remove });
  }
  return plan;
}

/** 채널을 넣을 카테고리를 고른다. 자리가 없으면 다음 번호로 새로 만든다. */
export async function pickCategory(guild, categoryPrefix) {
  if (guild.channels.cache.size >= SERVER_CHANNEL_LIMIT) {
    throw new Error(`channel_limit_reached_${guild.channels.cache.size}`);
  }
  const pattern = new RegExp(`^${categoryPrefix} (\\d+)$`);
  const categories = [...guild.channels.cache.values()]
    .filter(c => c.type === ChannelType.GuildCategory && pattern.test(c.name))
    .sort((a, b) => Number(a.name.match(pattern)[1]) - Number(b.name.match(pattern)[1]));
  for (const category of categories) {
    const used = [...guild.channels.cache.values()].filter(c => c.parentId === category.id).length;
    if (used + 2 <= CATEGORY_CHANNEL_LIMIT) return category;
  }
  const nextIndex = categories.length + 1;
  return guild.channels.create({
    name: `${categoryPrefix} ${nextIndex}`, type: ChannelType.GuildCategory,
    permissionOverwrites: [{ id: guild.roles.everyone.id, deny: [PermissionsBitField.Flags.ViewChannel] }],
    reason: "길드 채널 카테고리 확장",
  });
}

/** 공용 직책 역할 4종 확보. 권한은 전부 0 — 순수 표시용이다. */
export async function ensureRankRoles(guild, rankRoleIds) {
  for (const [rank, name] of Object.entries(RANK_ROLE_NAMES)) {
    const cached = rankRoleIds.get(rank);
    if (cached && guild.roles.cache.has(cached)) continue;
    let role = [...guild.roles.cache.values()].find(r => r.name === name);
    if (!role) {
      role = await guild.roles.create({ name, permissions: [], hoist: false, mentionable: false, reason: "길드 직책 표시 역할" });
    }
    rankRoleIds.set(rank, role.id);
  }
  return rankRoleIds;
}

/**
 * 없는 것만 만든다. 관리자가 채널을 지웠거나 작업이 중간에 끊겼어도 다시 돌리면 복구된다.
 *
 * ★저장된 id 가 없어도 먼저 "이름이 같은 역할"과 "그 역할이 걸린 채널"을 찾아본다.
 * 이 탐색이 없으면, 만들어 놓고 결과를 저장하기 전에 실패한 작업이 재시도될 때마다
 * 역할·채널을 새로 찍어내 중복이 쌓인다(2026-08-17 배포에서 러지 길드가 5벌까지 늘었다).
 */
export async function provisionGuild(guild, guildId, existing, categoryPrefix) {
  const current = existing ?? {};
  const roleName = `${GUILD_ROLE_PREFIX}${guildId}`.slice(0, 100);
  let role = current.roleId ? await guild.roles.fetch(current.roleId).catch(() => null) : null;
  if (!role) role = [...guild.roles.cache.values()].find(r => r.name === roleName) ?? null;
  if (!role) {
    role = await guild.roles.create({
      name: roleName,
      permissions: [], hoist: false, mentionable: false, reason: `길드 ${guildId} 채널 접근용`,
    });
  }
  const fetchChannel = async id => (id ? guild.channels.fetch(id).catch(() => null) : null);
  let text = await fetchChannel(current.textChannelId);
  let voice = await fetchChannel(current.voiceChannelId);
  let category = await fetchChannel(current.categoryId);
  // 길드 역할은 길드마다 유일하므로, 그 역할에 오버라이트가 걸린 채널이 곧 이 길드의 채널이다.
  // 이름 대조보다 정확하다(길드 이름이 정규화 과정에서 겹칠 수 있다).
  if (!text || !voice) {
    const owned = [...guild.channels.cache.values()].filter(c => c.permissionOverwrites?.cache?.has(role.id));
    text = text ?? owned.find(c => c.type === ChannelType.GuildText) ?? null;
    voice = voice ?? owned.find(c => c.type === ChannelType.GuildVoice) ?? null;
  }
  if (!category) category = text?.parent ?? voice?.parent ?? await pickCategory(guild, categoryPrefix);

  const overwrites = allow => ([
    { id: guild.roles.everyone.id, deny: [PermissionsBitField.Flags.ViewChannel] },
    { id: role.id, allow },
  ]);
  if (!text) {
    text = await guild.channels.create({
      name: textChannelName(guildId), type: ChannelType.GuildText, parent: category.id,
      permissionOverwrites: overwrites(TEXT_ALLOW), reason: `길드 ${guildId} 전용 채팅`,
    });
  }
  if (!voice) {
    voice = await guild.channels.create({
      name: String(guildId).slice(0, 90), type: ChannelType.GuildVoice, parent: category.id,
      permissionOverwrites: overwrites(VOICE_ALLOW), reason: `길드 ${guildId} 전용 음성`,
    });
  }
  return { roleId: role.id, categoryId: category.id, textChannelId: text.id, voiceChannelId: voice.id };
}

/** 채널을 지우면 대화도 같이 사라지므로, 삭제 전에 전문을 JSONL 로 떨군다. */
export async function archiveChannel(channel, guildId, archiveDir, log = console.log) {
  await mkdir(archiveDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const file = join(archiveDir, `${safeFileName(guildId)}-${stamp}.jsonl`);
  const collected = [];
  let before;
  let truncated = false;
  for (;;) {
    const batch = await channel.messages.fetch({ limit: 100, ...(before ? { before } : {}) });
    if (!batch.size) break;
    for (const message of batch.values()) {
      collected.push({
        id: message.id,
        at: new Date(message.createdTimestamp).toISOString(),
        authorId: message.author?.id ?? null,
        authorTag: message.author?.tag ?? null,
        content: message.content ?? "",
        attachments: [...message.attachments.values()].map(a => ({ name: a.name, url: a.url })),
        embeds: message.embeds.length,
      });
    }
    before = batch.last().id;
    if (collected.length >= ARCHIVE_MESSAGE_CAP) { truncated = true; break; }
  }
  collected.sort((a, b) => (a.at < b.at ? -1 : a.at > b.at ? 1 : 0));
  const header = {
    type: "meta", guildId, channelId: channel.id, channelName: channel.name,
    messages: collected.length, truncated, archivedAt: new Date().toISOString(),
  };
  let buffer = `${JSON.stringify(header)}\n`;
  for (const entry of collected) {
    buffer += `${JSON.stringify({ type: "message", ...entry })}\n`;
    if (buffer.length > 512_000) { await appendFile(file, buffer, "utf8"); buffer = ""; }
  }
  if (buffer) await appendFile(file, buffer, "utf8");
  log(`[Guild] archived ${collected.length} messages of ${guildId} to ${file}${truncated ? " (truncated)" : ""}`);
  return { file, messages: collected.length, truncated };
}

export async function deprovisionGuild(guild, guildId, discord, archiveDir, log = console.log) {
  if (discord?.textChannelId) {
    const text = await guild.channels.fetch(discord.textChannelId).catch(() => null);
    if (text) {
      await archiveChannel(text, guildId, archiveDir, log);
      await text.delete(`길드 ${guildId} 해체`);
    }
  }
  if (discord?.voiceChannelId) {
    const voice = await guild.channels.fetch(discord.voiceChannelId).catch(() => null);
    if (voice) await voice.delete(`길드 ${guildId} 해체`);
  }
  if (discord?.roleId) {
    const role = await guild.roles.fetch(discord.roleId).catch(() => null);
    if (role) await role.delete(`길드 ${guildId} 해체`);
  }
}

// 전체 멤버 목록 요청(게이트웨이 opcode 8)은 레이트리밋이 빡빡하다. 길드 작업마다 부르면
// 여러 길드를 연달아 동기화할 때 바로 걸린다. GuildMembers 인텐트가 켜져 있으면 이후 변동은
// 이벤트로 캐시에 반영되므로, 처음 한 번만 받아오고 캐시가 비어 보일 때만 다시 받는다.
const hydrated = new Set();
async function hydrateMembers(guild) {
  if (hydrated.has(guild.id) && guild.members.cache.size >= (guild.memberCount ?? 0)) return;
  await guild.members.fetch();
  hydrated.add(guild.id);
}

/** 계획을 세우고 실제 역할 부여/회수까지 수행한다. */
export async function syncMembers(guild, guildId, discord, targets, rankRoleIds) {
  if (!discord?.roleId) throw new Error("guild_role_not_provisioned");
  const role = await guild.roles.fetch(discord.roleId).catch(() => null);
  if (!role) throw new Error("guild_role_gone");
  await ensureRankRoles(guild, rankRoleIds);
  await hydrateMembers(guild);

  const allGuildRoleIds = new Set(
    [...guild.roles.cache.values()].filter(r => r.name.startsWith(GUILD_ROLE_PREFIX)).map(r => r.id)
  );
  const holders = new Map();
  for (const member of role.members.values()) holders.set(member.id, [...member.roles.cache.keys()]);
  for (const target of targets) {
    if (!target.discordId || holders.has(target.discordId)) continue;
    const member = guild.members.cache.get(target.discordId);
    if (member) holders.set(target.discordId, [...member.roles.cache.keys()]);
  }

  const plan = planMemberSync({ guildRoleId: role.id, rankRoleIds, targets, holders, allGuildRoleIds });
  for (const step of plan) {
    const member = guild.members.cache.get(step.discordId);
    if (!member) continue;
    if (step.add.length) await member.roles.add(step.add, `길드 ${guildId} 동기화`);
    if (step.remove.length) await member.roles.remove(step.remove, `길드 ${guildId} 동기화`);
  }
  return plan.length;
}
