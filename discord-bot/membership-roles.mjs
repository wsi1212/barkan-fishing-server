// 멤버십 표시 역할(VIP / MVP / MVP+).
//
// 권한 자체는 Discord 서버에서 역할에 설정한다. 봇이 새로 만들어야 하는 경우에는
// 아무 권한도 없는 표시 역할로 만들고, 같은 이름의 기존 역할이 있으면 그 역할을 재사용한다.
// 한 사람에게는 활성 멤버십 등급 하나만 남기며 만료되면 세 역할을 모두 회수한다.

export const MEMBERSHIP_ROLES = Object.freeze({
  VIP: {
    name: (process.env.DISCORD_VIP_ROLE_NAME ?? "").trim() || "VIP",
    color: 0x83E7FF,
  },
  MVP: {
    name: (process.env.DISCORD_MVP_ROLE_NAME ?? "").trim() || "MVP",
    color: 0xFFD36B,
  },
  MVP_PLUS: {
    name: (process.env.DISCORD_MVP_PLUS_ROLE_NAME ?? "").trim() || "MVP+",
    color: 0xFF94DA,
  },
});

/** 저장된 id가 없거나 사라졌으면 이름으로 찾고, 정말 없을 때만 만든다. */
export async function ensureMembershipRoles(guild, roleIds) {
  let refreshed = false;
  for (const [tier, spec] of Object.entries(MEMBERSHIP_ROLES)) {
    const cached = roleIds.get(tier);
    if (cached) {
      const known = guild.roles.cache.get(cached) ?? await guild.roles.fetch(cached).catch(() => null);
      if (known) continue;
      console.warn(`[Membership] ${spec.name} 역할 id ${cached} 를 찾을 수 없어 이름으로 다시 찾습니다.`);
    }
    if (!refreshed) {
      await guild.roles.fetch();
      refreshed = true;
    }
    let role = [...guild.roles.cache.values()].find(candidate => candidate.name === spec.name);
    if (!role) {
      role = await guild.roles.create({
        name: spec.name,
        colors: { primaryColor: spec.color },
        permissions: [],
        hoist: false,
        mentionable: false,
        reason: "바르칸 멤버십 표시 역할",
      });
      console.log(`[Membership] created role ${spec.name} (${role.id})`);
    }
    roleIds.set(tier, role.id);
  }
  return roleIds;
}

/** 활성 tier 역할 하나만 남긴다. tier가 없거나 잘못됐으면 멤버십 역할을 전부 회수한다. */
export async function applyMembershipRole(member, tier, roleIds) {
  await ensureMembershipRoles(member.guild, roleIds);
  const activeTier = Object.hasOwn(MEMBERSHIP_ROLES, tier) ? tier : null;
  const keep = activeTier ? roleIds.get(activeTier) : null;
  let changed = false;

  for (const [candidate, roleId] of roleIds) {
    if (candidate !== activeTier && roleId && member.roles.cache.has(roleId)) {
      await member.roles.remove(roleId, "멤버십 등급 변경 또는 만료");
      changed = true;
    }
  }
  if (keep && !member.roles.cache.has(keep)) {
    await member.roles.add(keep, `멤버십 ${MEMBERSHIP_ROLES[activeTier].name} 활성`);
    changed = true;
  }
  return { tier: activeTier, changed };
}
