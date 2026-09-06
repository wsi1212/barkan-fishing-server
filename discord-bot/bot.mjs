import { Client, GatewayIntentBits, MessageFlags, REST, Routes, SlashCommandBuilder } from "discord.js";
import { deprovisionGuild, ensureRankRoles, provisionGuild, syncMembers } from "./guild-sync.mjs";
import { EDITION_ROLES, applyEditionRole, ensureEditionRoles } from "./edition-roles.mjs";

const required = (name) => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is not set`);
  return value;
};
const TOKEN = required("DISCORD_BOT_TOKEN");
const GUILD_ID = required("DISCORD_GUILD_ID");
const CHANNEL_ID = required("DISCORD_CHANNEL_ID");
const ROLE_ID = required("DISCORD_VERIFIED_ROLE_ID");
const API_URL = (process.env.DISCORD_LINK_API_URL ?? "http://127.0.0.1:3100").replace(/\/$/, "");
const INTERNAL_TOKEN = (process.env.DISCORD_INTERNAL_TOKEN ?? process.env.INTERNAL_API_TOKEN ?? "").trim();
if (!INTERNAL_TOKEN) throw new Error("DISCORD_INTERNAL_TOKEN or INTERNAL_API_TOKEN is not set");
// 해체된 길드의 채팅은 지우기 전에 여기에 JSONL 로 남긴다. systemd ReadWritePaths 안이어야 쓸 수 있다.
const ARCHIVE_DIR = process.env.GUILD_ARCHIVE_DIR ?? "/srv/barkan-discord-bot/archive";
const CATEGORY_PREFIX = process.env.GUILD_CATEGORY_PREFIX ?? "길드";
// 에디션 표시 역할(자바/베드락) id. 비워 두면 봇이 이름으로 찾거나 직접 만든다.
const editionRoleIds = new Map(
  [["java", (process.env.DISCORD_JAVA_ROLE_ID ?? "").trim()],
   ["bedrock", (process.env.DISCORD_BEDROCK_ROLE_ID ?? "").trim()]].filter(([, id]) => id)
);

// GuildMembers 는 특권 인텐트다. 개발자 포털에서 켜지 않으면 역할 회수와 재입장 복구가 조용히 동작하지 않는다.
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers] });
const command = new SlashCommandBuilder()
  .setName("인증")
  .setDescription("마인크래프트 계정을 이 Discord 서버에 연결합니다.")
  .addStringOption(option => option.setName("코드").setDescription("게임에서 /디스코드로 받은 코드").setRequired(true).setMaxLength(16));

function messageFor(error) {
  return {
    code_invalid: "코드가 없거나 만료됐어요. 게임에서 /디스코드를 다시 입력해 새 코드를 받아주세요.",
    minecraft_already_linked: "이 마인크래프트 계정은 이미 다른 Discord 계정과 연결되어 있어요.",
    discord_already_linked: "이 Discord 계정은 이미 다른 마인크래프트 계정과 연결되어 있어요.",
    invalid_request: "인증 코드 형식이 올바르지 않아요. 예: BK-AB12CD34",
    role_missing_permissions: "연결은 확인됐지만 인증 역할을 지급할 권한이 없어요. 서버 관리자에게 봇 역할을 '인증됨' 역할보다 위로 올려달라고 해주세요. 역할을 올린 뒤 게임에서 /디스코드를 다시 입력하면 됩니다.",
  }[error] ?? "인증 처리 중 문제가 생겼어요. 잠시 후 다시 시도해주세요.";
}

async function api(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${INTERNAL_TOKEN}`, "Content-Type": "application/json", ...(options.headers ?? {}) },
  });
  if (!response.ok) throw new Error(`api_${response.status}_${path}`);
  return response.json();
}

async function linkCode(code, discordId, discordName) {
  const response = await fetch(`${API_URL}/internal/discord/link`, {
    method: "POST",
    headers: { Authorization: `Bearer ${INTERNAL_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ code, discordId, discordName }),
  });
  let body = {};
  try { body = await response.json(); } catch { /* malformed upstream response */ }
  if (!response.ok) throw new Error(body.error ?? "link_failed");
  return body;
}

async function markVerified(minecraftUuid, discordId) {
  const response = await fetch(`${API_URL}/internal/discord/verified`, {
    method: "POST",
    headers: { Authorization: `Bearer ${INTERNAL_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify({ minecraftUuid, discordId }),
  });
  if (!response.ok) throw new Error(`verified_mark_failed_${response.status}`);
}

const rest = new REST({ version: "10" }).setToken(TOKEN);
let registerTimer;
async function registerCommands(user) {
  try {
    await rest.put(Routes.applicationGuildCommands(user.id, GUILD_ID), { body: [command.toJSON()] });
    console.log(`[Discord] logged in as ${user.tag}; /인증 registered for guild ${GUILD_ID}`);
    const guild = client.guilds.cache.get(GUILD_ID) ?? await client.guilds.fetch(GUILD_ID);
    const targetRole = await guild.roles.fetch(ROLE_ID);
    const botMember = await guild.members.fetch(user.id);
    if (!targetRole) {
      console.error(`[Discord] configured verified role ${ROLE_ID} was not found in guild ${GUILD_ID}`);
    } else if (botMember.roles.highest.position <= targetRole.position) {
      console.error(`[Discord] role hierarchy: move the bot role above '${targetRole.name}' (${ROLE_ID}) to grant it`);
    }
    // 에디션 역할은 없으면 여기서 만든다. 실패해도 /인증 등록 재시도 루프에 말려들지 않도록 따로 감싼다.
    try {
      await ensureEditionRoles(guild, editionRoleIds);
      for (const id of editionRoleIds.values()) {
        const role = guild.roles.cache.get(id) ?? await guild.roles.fetch(id).catch(() => null);
        if (role && botMember.roles.highest.position <= role.position) {
          console.error(`[Discord] role hierarchy: move the bot role above '${role.name}' (${id}) to grant it`);
        }
      }
    } catch (error) {
      console.error(`[Discord] edition role setup failed (${error?.message ?? error}); Manage Roles 권한을 확인하세요`);
    }
    if (registerTimer) clearInterval(registerTimer);
  } catch (error) {
    console.error(`[Discord] /인증 registration failed (${error.code ?? "unknown"}); invite the bot to guild ${GUILD_ID} with applications.commands, then retrying in 30s`);
    if (!registerTimer) registerTimer = setInterval(() => registerCommands(user), 30_000);
  }
}

client.on("interactionCreate", interaction => {
  if (!interaction.isChatInputCommand() || interaction.commandName !== "인증") return;
  void handleVerification(interaction);
});

async function handleVerification(interaction) {
  const ageMs = () => Date.now() - interaction.createdTimestamp;
  if (interaction.guildId !== GUILD_ID || interaction.channelId !== CHANNEL_ID) {
    try {
      await interaction.reply({ content: "이 명령어는 지정된 마인크래프트 채널에서만 사용할 수 있어요.", flags: MessageFlags.Ephemeral });
    } catch (error) {
      console.warn(`[Discord] interaction reply failed code=${error?.code ?? "unknown"} ageMs=${ageMs()}`);
    }
    return;
  }
  // Discord의 3초 ACK 제한을 넘기지 않도록 코드 검증/API 호출보다 먼저 응답을 예약한다.
  try {
    await interaction.deferReply({ flags: MessageFlags.Ephemeral });
  } catch (error) {
    console.warn(`[Discord] interaction ACK failed code=${error?.code ?? "unknown"} ageMs=${ageMs()}`);
    return;
  }
  const code = interaction.options.getString("코드", true).trim();
  try {
    const linked = await linkCode(code, interaction.user.id, interaction.user.tag);
    const member = await interaction.guild.members.fetch(interaction.user.id);
    try {
      await member.roles.add(ROLE_ID, "마인크래프트 계정 인증");
    } catch (error) {
      if (error?.code === 50013 || /missing permissions/i.test(error?.message ?? "")) {
        throw new Error("role_missing_permissions");
      }
      throw error;
    }
    try {
      await markVerified(linked.minecraftUuid, interaction.user.id);
    } catch (error) {
      // 역할은 이미 지급됐으므로 인증 응답은 성공으로 처리하고, 캐시 보상은 재시도 가능하게 로그만 남긴다.
      console.warn(`[Discord] verified mark failed for discord=${interaction.user.id}: ${error.message}`);
    }
    let edition = null;
    try {
      ({ edition } = await applyEditionRole(member, linked.minecraftUuid, editionRoleIds));
    } catch (error) {
      // 표시용 역할이다. Manage Roles 누락·역할 순서 문제로 실패해도 인증은 성공으로 끝낸다.
      console.warn(`[Discord] edition role failed for discord=${interaction.user.id}: ${error?.message ?? error}`);
    }
    const editionNote = edition ? ` 에디션은 **${EDITION_ROLES[edition].name}** 로 표시됩니다.` : "";
    await interaction.editReply(`인증 완료! **${linked.playerName}** 계정과 연결됐고 인증 역할을 지급했어요.${editionNote}`);
    if (!linked.retry) {
      try {
        await interaction.channel.send({
          content: `✅ **${linked.playerName}**님이 마인크래프트 계정 인증에 성공했습니다.`,
          allowedMentions: { parse: [] },
        });
      } catch (error) {
        console.warn(`[Discord] public verification message failed code=${error?.code ?? "unknown"}`);
      }
    }
    console.log(`[Discord] linked minecraft=${linked.minecraftUuid} discord=${interaction.user.id}`);
  } catch (error) {
    try { await interaction.editReply(messageFor(error.message)); }
    catch (replyError) { console.warn(`[Discord] error reply failed code=${replyError?.code ?? "unknown"} ageMs=${ageMs()}`); }
    console.warn(`[Discord] link failed for discord=${interaction.user.id}: ${error.message}`);
  }
}

// ===== 길드 전용 채널·역할 =====
// 백엔드(vip-billing)가 게임 길드 명부와 디스코드 현황을 비교해 작업만 큐에 남긴다. 여기서는 큐를 비운다.
// 실제 조작 로직은 guild-sync.mjs 에 있다(테스트 가능하게 분리).

const rankRoleIds = new Map();

async function homeGuild() {
  return client.guilds.cache.get(GUILD_ID) ?? await client.guilds.fetch(GUILD_ID);
}

async function runJob(job) {
  const guild = await homeGuild();
  if (job.kind === "guild_delete") {
    await deprovisionGuild(guild, job.guildId, job.discord, ARCHIVE_DIR);
    return { removed: true };
  }
  await ensureRankRoles(guild, rankRoleIds);
  const discord = await provisionGuild(guild, job.guildId, job.discord, CATEGORY_PREFIX);
  // ★만든 즉시 저장한다. 뒤이은 멤버 동기화가 실패하면 작업 전체가 실패로 보고되는데,
  //   그때 id 가 저장돼 있지 않으면 재시도가 역할·채널을 새로 찍어내 중복이 쌓인다.
  const changed = !job.discord || Object.entries(discord).some(([key, value]) => job.discord[key] !== value);
  if (changed) {
    await api("/internal/guild/jobs/result", {
      method: "POST",
      body: JSON.stringify({ id: 0, guildId: job.guildId, ok: true, discord }),
    });
  }
  await syncMembers(guild, job.guildId, discord, job.members ?? [], rankRoleIds);
  return { discord };
}

let draining = false;
async function drainGuildJobs() {
  if (draining || !client.isReady()) return;
  draining = true;
  try {
    const { jobs } = await api("/internal/guild/jobs");
    for (const job of jobs ?? []) {
      try {
        const outcome = await runJob(job);
        await api("/internal/guild/jobs/result", {
          method: "POST",
          body: JSON.stringify({ id: job.id, guildId: job.guildId, ok: true, ...outcome }),
        });
        console.log(`[Guild] ${job.kind} ${job.guildId} done`);
      } catch (error) {
        await api("/internal/guild/jobs/result", {
          method: "POST",
          body: JSON.stringify({ id: job.id, guildId: job.guildId, ok: false, error: String(error?.message ?? error) }),
        }).catch(() => {});
        console.warn(`[Guild] ${job.kind} ${job.guildId} failed (attempt ${job.attempts}): ${error?.message ?? error}`);
      }
    }
  } catch (error) {
    console.warn(`[Guild] job poll failed: ${error?.message ?? error}`);
  } finally {
    draining = false;
  }
}

/** 관리자가 채널을 지웠거나 봇이 꺼져 있는 동안 벌어진 어긋남을 주기적으로 되돌린다. */
async function reconcileGuilds() {
  if (!client.isReady()) return;
  try {
    const guild = await homeGuild();
    await ensureRankRoles(guild, rankRoleIds);
    const { guilds } = await api("/internal/guild/state");
    for (const entry of guilds ?? []) {
      try {
        const discord = await provisionGuild(guild, entry.guildId, entry.discord, CATEGORY_PREFIX);
        await syncMembers(guild, entry.guildId, discord, entry.members ?? [], rankRoleIds);
        const changed = !entry.discord || Object.entries(discord).some(([key, value]) => entry.discord[key] !== value);
        if (changed) {
          await api("/internal/guild/jobs/result", {
            method: "POST",
            body: JSON.stringify({ id: 0, guildId: entry.guildId, ok: true, discord }),
          });
          console.log(`[Guild] reconciled ${entry.guildId}`);
        }
      } catch (error) {
        console.warn(`[Guild] reconcile ${entry.guildId} failed: ${error?.message ?? error}`);
      }
    }
  } catch (error) {
    console.warn(`[Guild] reconcile failed: ${error?.message ?? error}`);
  }
}

// 디스코드를 나갔다 들어오면 역할이 전부 사라진다. 소속 길드를 찾아 다시 채워준다.
client.on("guildMemberAdd", member => {
  if (member.guild.id !== GUILD_ID) return;
  void (async () => {
    try {
      const { guilds } = await api("/internal/guild/state");
      const mine = (guilds ?? []).find(entry => (entry.members ?? []).some(m => m.discordId === member.id));
      if (!mine?.discord) return;
      await syncMembers(member.guild, mine.guildId, mine.discord, mine.members, rankRoleIds);
      console.log(`[Guild] restored roles for rejoining member ${member.id} (${mine.guildId})`);
    } catch (error) {
      console.warn(`[Guild] rejoin restore failed for ${member.id}: ${error?.message ?? error}`);
    }
  })();
});

/**
 * 이미 인증을 끝낸 사람에게도 에디션 역할을 채운다.
 *
 * 인증 시점 지급만 두면 «이 기능이 생기기 전에 인증한 사람» 이 영원히 빈칸으로 남고,
 * 디스코드를 나갔다 들어오면 역할이 전부 날아간다(길드 역할과 같은 사정). 여기서 복구한다.
 * vip-billing 이 아직 /internal/discord/links 를 모르는 구버전이면 이번 회차만 건너뛴다 —
 * 봇을 먼저 배포해도 인증 시점 지급은 그대로 돌고, vip-billing 이 올라오면 봇 재시작 없이 이어진다.
 * (404 를 영구히 끄면 배포 순서가 함정이 된다.)
 */
let backfill404Warned = false;
async function reconcileEditions() {
  if (!client.isReady()) return;
  let links;
  try {
    ({ links } = await api("/internal/discord/links"));
    backfill404Warned = false;
  } catch (error) {
    const message = String(error?.message ?? error);
    if (message.startsWith("api_404_")) {
      if (!backfill404Warned) {
        console.warn("[Discord] vip-billing 에 /internal/discord/links 가 아직 없어 에디션 백필을 건너뜁니다(인증 시점 지급은 정상).");
        backfill404Warned = true;
      }
      return;
    }
    console.warn(`[Discord] edition backfill poll failed: ${message}`);
    return;
  }
  try {
    const guild = await homeGuild();
    await ensureEditionRoles(guild, editionRoleIds);
    let changed = 0;
    for (const link of links ?? []) {
      // ★멤버 전체 fetch(게이트웨이 opcode 8)를 쓰지 않는다 — 20초 뒤 도는 길드 reconcile 이
      //   같은 요청을 하고 있어서 둘이 겹치면 "opcode 8 rate limited" 로 통째로 실패한다.
      //   id 지정 fetch 는 REST 라 겹치지 않고, 캐시가 차면 그마저도 안 나간다.
      const member = guild.members.cache.get(link.discordId)
        ?? await guild.members.fetch(link.discordId).catch(() => null);
      if (!member) continue; // 디스코드 서버를 나간 사람
      try {
        if ((await applyEditionRole(member, link.minecraftUuid, editionRoleIds)).changed) changed += 1;
      } catch (error) {
        console.warn(`[Discord] edition role failed for ${link.discordId}: ${error?.message ?? error}`);
      }
    }
    if (changed) console.log(`[Discord] edition roles reconciled (${changed} changed)`);
  } catch (error) {
    console.warn(`[Discord] edition backfill failed: ${error?.message ?? error}`);
  }
}

client.once("ready", ready => {
  void registerCommands(ready.user);
  setInterval(() => void drainGuildJobs(), 5_000);
  setInterval(() => void reconcileGuilds(), 30 * 60_000);
  setTimeout(() => void reconcileGuilds(), 20_000);
  setInterval(() => void reconcileEditions(), 30 * 60_000);
  setTimeout(() => void reconcileEditions(), 45_000);   // 길드 reconcile(20초)과 겹치지 않게
});

client.on("error", error => console.error("[Discord] client error", error));
process.on("unhandledRejection", error => console.error("[Discord] unhandled rejection", error));

// GuildMembers 는 특권 인텐트라 포털에서 꺼져 있으면 로그인 자체가 거부된다(게이트웨이 4014).
// 그대로 두면 systemd 가 무한 재시작하면서 원인 모를 장애처럼 보이므로, 진단을 분명히 남기고 죽는다.
client.login(TOKEN).catch(error => {
  const message = String(error?.message ?? error);
  if (error?.code === "DisallowedIntents" || /disallowed intent/i.test(message)) {
    console.error("[Discord] SERVER MEMBERS INTENT 가 꺼져 있어 로그인이 거부됐습니다.");
    console.error("[Discord] 개발자 포털 → Bot → Privileged Gateway Intents 에서 SERVER MEMBERS INTENT 를 켠 뒤 재시작하세요.");
  }
  console.error("[Discord] login failed", error);
  process.exit(1);
});
