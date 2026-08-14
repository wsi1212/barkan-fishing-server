import { Client, GatewayIntentBits, MessageFlags, REST, Routes, SlashCommandBuilder } from "discord.js";

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

const client = new Client({ intents: [GatewayIntentBits.Guilds] });
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
    if (registerTimer) clearInterval(registerTimer);
  } catch (error) {
    console.error(`[Discord] /인증 registration failed (${error.code ?? "unknown"}); invite the bot to guild ${GUILD_ID} with applications.commands, then retrying in 30s`);
    if (!registerTimer) registerTimer = setInterval(() => registerCommands(user), 30_000);
  }
}

client.once("ready", ready => {
  void registerCommands(ready.user);
});

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
    await interaction.editReply(`인증 완료! **${linked.playerName}** 계정과 연결됐고 인증 역할을 지급했어요.`);
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

client.on("error", error => console.error("[Discord] client error", error));
process.on("unhandledRejection", error => console.error("[Discord] unhandled rejection", error));
client.login(TOKEN);
