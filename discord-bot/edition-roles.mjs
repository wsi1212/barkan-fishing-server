// 에디션 표시 역할 (자바 / 베드락).
//
// 권한이 하나도 없는 «보는 용» 역할이다. 디스코드 멤버 목록에서 누가 어느 에디션으로 노는지
// 한눈에 보이게 하는 것 말고는 아무 일도 하지 않는다.
//
// ★판정 기준은 디스코드 접속 기기(모바일/데스크톱)가 아니라 «연결된 마크 계정» 이다.
//   Floodgate 는 베드락 유저에게 new UUID(0, xuid) 를 주므로 상위 64비트가 전부 0이다
//   (prod 실측: 00000000-0000-0000-0009-01f758e05895). 서버가 이미 아는 사실이라 100% 맞다.
//   기기로 판정하면 ①PC 로 자바를 하면서 폰으로 인증하는 흔한 경우를 베드락으로 찍고
//   ②PRESENCE 특권 인텐트가 따로 필요하며 ③온라인 상태가 오프라인·투명이면 아예 안 보인다.
//   즉 역할이 «주장하는 사실»과 어긋난다. 기기 표시가 필요해지면 그건 별도 역할로 둘 것.

export const EDITION_ROLES = {
  java:    { name: (process.env.DISCORD_JAVA_ROLE_NAME ?? "").trim() || "자바", color: 0x3FA34D },
  bedrock: { name: (process.env.DISCORD_BEDROCK_ROLE_NAME ?? "").trim() || "베드락", color: 0x4FA8DC },
};

/** Floodgate(베드락) UUID 는 상위 64비트가 0이라 RFC 의 버전·변종 니블이 없다. */
export function editionOf(minecraftUuid) {
  return /^0{8}-0{4}-0{4}-/.test(String(minecraftUuid ?? "").trim()) ? "bedrock" : "java";
}

/**
 * 없으면 만들고, 같은 이름이 이미 있으면 그걸 쓴다(ensureRankRoles 와 같은 규칙).
 * 운영자가 손으로 만들어 둔 역할을 중복으로 찍어내지 않기 위한 것이다.
 */
export async function ensureEditionRoles(guild, editionRoleIds) {
  let refreshed = false;
  for (const [edition, spec] of Object.entries(EDITION_ROLES)) {
    const cached = editionRoleIds.get(edition);
    if (cached) {
      const known = guild.roles.cache.get(cached) ?? await guild.roles.fetch(cached).catch(() => null);
      if (known) continue;
      console.warn(`[Discord] ${spec.name} 역할 id ${cached} 를 찾을 수 없어 이름으로 다시 찾습니다.`);
    }
    // ★이름으로 찾기 전에 역할 목록을 한 번 새로 고친다. 캐시가 덜 찬 상태에서 조회하면
    //   "없다"고 보고 역할을 새로 찍어낸다(길드 역할에서 실제로 겪은 중복 누적과 같은 사고).
    //   id 가 이미 유효한 정상 경로에서는 여기까지 오지 않으므로 REST 호출도 없다.
    if (!refreshed) {
      await guild.roles.fetch();
      refreshed = true;
    }
    let role = [...guild.roles.cache.values()].find(r => r.name === spec.name);
    if (!role) {
      role = await guild.roles.create({
        // discord.js 14.22+ 는 단색 `color` 를 deprecated 로 본다(다색 역할이 생기면서).
        name: spec.name, colors: { primaryColor: spec.color }, permissions: [],
        hoist: false, mentionable: false, reason: "마크 에디션 표시 역할",
      });
      console.log(`[Discord] created edition role ${spec.name} (${role.id})`);
    }
    editionRoleIds.set(edition, role.id);
  }
  return editionRoleIds;
}

/**
 * 에디션 역할을 하나만 남긴다 — 반대쪽은 회수한다(계정을 갈아끼웠거나 관리자가 잘못 준 경우).
 * 표시용이라 실패해도 인증 결과를 바꾸지 않는다. 호출부가 catch 한다.
 */
export async function applyEditionRole(member, minecraftUuid, editionRoleIds) {
  const edition = editionOf(minecraftUuid);
  await ensureEditionRoles(member.guild, editionRoleIds);
  const keep = editionRoleIds.get(edition);
  const drop = editionRoleIds.get(edition === "bedrock" ? "java" : "bedrock");
  let changed = false;
  if (drop && member.roles.cache.has(drop)) {
    await member.roles.remove(drop, "에디션 표시 역할 정정");
    changed = true;
  }
  if (keep && !member.roles.cache.has(keep)) {
    await member.roles.add(keep, "마크 에디션 표시");
    changed = true;
  }
  return { edition, changed };
}
