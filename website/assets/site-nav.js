(() => {
  let host = document.querySelector('[data-site-nav]');
  if (!host) {
    const legacyNav = document.querySelector('nav.nav[aria-label="주 메뉴"], nav.nav');
    if (!legacyNav) return;
    host = document.createElement('div');
    host.dataset.siteNav = '';
    legacyNav.replaceWith(host);
  }

  const groups = [
    {
      id: 'world', label: '세계', summary: '바르칸 열도의 풍경과 이야기',
      items: [
        ['/','홈','섬과 항구의 첫 화면'],
        ['/map','항해 지도','실측 좌표와 지역 영역 보기'],
        ['/#world','세계 둘러보기','지역과 생활 시스템 살펴보기'],
        ['/wiki/explore','섬·탐험 위키','섬, 채집, 수집품 기록']
      ]
    },
    {
      id: 'guide', label: '시작하기', summary: '처음 항해하는 사람을 위한 안내',
      items: [
        ['/wiki/start','입항 안내','서버 접속과 첫 낚시'],
        ['/wiki/fishing','낚시 가이드','미니게임과 등급 이해하기'],
        ['/wiki','전체 위키','모든 시스템 문서 보기']
      ]
    },
    {
      id: 'archive', label: '도감·위키', summary: '바르칸의 아이템과 생물 기록',
      items: [
        ['/dex','물고기 도감','565종 어종과 서식 조건'],
        ['/gear','장비 도감','낚싯대·작살·부품'],
        ['/catalog','재료·채집 도감','재료와 채집품의 획득처'],
        ['/wiki/gear','장비·강화 위키','부품 조합과 강화 흐름']
      ]
    },
    {
      id: 'community', label: '커뮤니티', summary: '항해자들의 기록과 경쟁',
      items: [
        ['/community','게시판','공략과 플레이 기록'],
        ['/community/guilds','길드','길드 목록과 섬 프로필'],
        ['/ranking','랭킹','어종·길드·섬 기록 비교']
      ]
    },
    {
      id: 'shop', label: '상점', summary: '원하는 방식으로 항해를 꾸리기',
      items: [
        ['/vip/','멤버십 상점','VIP·MVP·MVP+ 이용권'],
        ['https://discord.gg/fWVGGEbBsd','디스코드','공지와 실시간 커뮤니티']
      ]
    }
  ];

  if (!document.getElementById('barkan-site-nav-style')) {
    const style = document.createElement('style');
    style.id = 'barkan-site-nav-style';
    style.textContent = `
      .barkan-site-nav{--nav-text:#e8eee4;--nav-muted:#a7bbb1;--nav-faint:#769289;--nav-accent:#d6a05c;--nav-line:rgba(211,231,218,.23);--nav-soft-line:rgba(211,231,218,.13);position:relative;z-index:30;display:flex;height:72px;align-items:center;gap:30px;border-bottom:1px solid var(--nav-line);font-family:Barkan,"Barkan Aggro","Apple SD Gothic Neo","Noto Sans KR",sans-serif}
      .barkan-site-brand{flex:0 0 auto;line-height:1;color:inherit;text-decoration:none}.barkan-site-brand strong{display:block;font-size:20px;font-weight:800;letter-spacing:.15em}.barkan-site-brand small{display:block;margin-top:7px;color:var(--nav-accent);font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:8px;font-weight:700;letter-spacing:.22em}
      .barkan-site-links{display:flex;align-items:stretch;align-self:stretch;gap:3px;min-width:0}.barkan-site-group{position:relative;display:flex;align-items:center}.barkan-site-tab{display:inline-flex;height:100%;align-items:center;gap:7px;padding:0 11px;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--nav-muted);font:700 12px Barkan,"Barkan Aggro","Apple SD Gothic Neo","Noto Sans KR",sans-serif;cursor:pointer;white-space:nowrap}.barkan-site-tab svg{width:13px;height:13px;fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.8;transition:transform .18s ease}.barkan-site-tab:hover,.barkan-site-tab:focus-visible,.barkan-site-tab[aria-expanded="true"],.barkan-site-group.is-current .barkan-site-tab{border-bottom-color:var(--nav-accent);color:var(--nav-accent)}.barkan-site-tab[aria-expanded="true"] svg{transform:rotate(180deg)}
      .barkan-site-direct{display:inline-flex;height:100%;align-items:center;padding:0 13px;border-bottom:2px solid transparent;color:var(--nav-muted);font:700 12px Barkan,"Barkan Aggro","Apple SD Gothic Neo","Noto Sans KR",sans-serif;text-decoration:none;white-space:nowrap}.barkan-site-direct:hover,.barkan-site-direct:focus-visible,.barkan-site-direct[aria-current="page"]{border-bottom-color:var(--nav-accent);color:var(--nav-accent)}
      .barkan-site-panel{position:absolute;z-index:5;top:100%;left:50%;width:min(430px,calc(100vw - 30px));padding:18px;border:1px solid var(--nav-line);background:rgba(7,24,24,.98);box-shadow:0 18px 45px rgba(0,0,0,.34);backdrop-filter:blur(16px);transform:translateX(-50%)}.barkan-site-panel[hidden]{display:none}.barkan-site-panel-head{margin:0 0 13px;color:var(--nav-faint);font:700 9px/1.4 ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;letter-spacing:.1em;text-transform:uppercase}.barkan-site-panel-grid{display:grid;grid-template-columns:1fr;gap:1px;border-top:1px solid var(--nav-soft-line);border-left:1px solid var(--nav-soft-line)}.barkan-site-panel-grid a{display:flex;min-height:44px;align-items:center;gap:14px;padding:10px 12px;border-right:1px solid var(--nav-soft-line);border-bottom:1px solid var(--nav-soft-line);color:var(--nav-text);text-decoration:none;white-space:nowrap}.barkan-site-panel-grid a:hover,.barkan-site-panel-grid a:focus-visible,.barkan-site-panel-grid a[aria-current="page"]{background:rgba(35,91,78,.34);color:var(--nav-accent)}.barkan-site-panel-grid strong{flex:0 0 auto;overflow:hidden;font-size:13px;font-weight:700;text-overflow:ellipsis;white-space:nowrap}.barkan-site-panel-grid span{min-width:0;margin:0;overflow:hidden;color:var(--nav-faint);font-size:10px;line-height:1.35;text-align:right;text-overflow:ellipsis;white-space:nowrap}.barkan-site-panel-grid a:hover span,.barkan-site-panel-grid a[aria-current="page"] span{color:var(--nav-muted)}
      .barkan-site-tools{display:flex;align-items:center;gap:10px;margin-left:auto}.barkan-site-profile{display:inline-flex;min-height:36px;align-items:center;padding:7px 12px;border:1px solid var(--nav-line);color:var(--nav-text);font-size:12px;text-decoration:none;white-space:nowrap}.barkan-site-profile:hover,.barkan-site-profile:focus-visible,.barkan-site-profile.is-profile{border-color:var(--nav-accent);color:var(--nav-accent)}.barkan-site-menu-toggle{display:none;min-height:36px;align-items:center;gap:9px;padding:7px 11px;border:1px solid var(--nav-line);background:rgba(8,21,22,.3);color:var(--nav-text);font:500 12px Barkan,"Barkan Aggro","Apple SD Gothic Neo","Noto Sans KR",sans-serif;cursor:pointer}.barkan-site-menu-toggle:hover,.barkan-site-menu-toggle:focus-visible,.barkan-site-menu-toggle[aria-expanded="true"]{border-color:var(--nav-accent);color:var(--nav-accent)}.barkan-site-menu-toggle i{display:grid;gap:3px;width:15px}.barkan-site-menu-toggle i span{display:block;height:1px;background:currentColor}
      .barkan-site-mobile-menu{position:absolute;z-index:5;top:calc(100% + 12px);right:0;width:min(430px,calc(100vw - 30px));padding:18px;border:1px solid var(--nav-line);background:rgba(7,24,24,.98);box-shadow:0 18px 45px rgba(0,0,0,.34);backdrop-filter:blur(16px)}.barkan-site-mobile-menu[hidden]{display:none}.barkan-site-mobile-primary{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:-2px 0 16px;padding:10px 0 14px;border-bottom:1px solid var(--nav-soft-line);color:var(--nav-text);text-decoration:none}.barkan-site-mobile-primary strong{color:var(--nav-accent);font-size:13px}.barkan-site-mobile-primary span{color:var(--nav-faint);font-size:10px}.barkan-site-mobile-primary:hover strong,.barkan-site-mobile-primary:focus-visible strong{color:var(--nav-text)}.barkan-site-mobile-group{padding:0 0 15px;margin-bottom:15px;border-bottom:1px solid var(--nav-soft-line)}.barkan-site-mobile-group:last-child{padding-bottom:0;margin-bottom:0;border-bottom:0}.barkan-site-mobile-group h2{margin:0 0 8px;color:var(--nav-accent);font-size:12px}.barkan-site-mobile-group a{display:flex;align-items:center;gap:12px;overflow:hidden;padding:7px 0;color:var(--nav-muted);font-size:13px;text-decoration:none;white-space:nowrap}.barkan-site-mobile-group strong{flex:0 0 auto}.barkan-site-mobile-group span{min-width:0;overflow:hidden;color:var(--nav-faint);font-size:10px;text-overflow:ellipsis;white-space:nowrap}.barkan-site-mobile-group a:hover,.barkan-site-mobile-group a:focus-visible,.barkan-site-mobile-group a[aria-current="page"]{color:var(--nav-text)}
      @media(max-width:980px){.barkan-site-nav{gap:18px}.barkan-site-links{gap:0}.barkan-site-tab{padding:0 7px;font-size:11px}.barkan-site-panel{width:min(390px,calc(100vw - 30px))}}
      @media(max-width:720px){.barkan-site-nav{height:72px}.barkan-site-links,.barkan-site-direct{display:none}.barkan-site-tools{gap:6px}.barkan-site-profile{padding:7px 9px;font-size:11px}.barkan-site-menu-toggle{display:inline-flex;padding:7px 9px}.barkan-site-mobile-menu{right:-1px}}
      @media(prefers-reduced-motion:reduce){.barkan-site-tab svg{transition:none}}
    `;
    document.head.append(style);
  }

  const chevron = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4"></path></svg>';
  const itemMarkup = ([href, title, description]) => `<a href="${href}"${href.startsWith('http') ? ' target="_blank" rel="noopener noreferrer"' : ''}><strong>${title}</strong><span>${description}</span></a>`;
  const desktopGroups = groups.map(group => `<div class="barkan-site-group" data-menu-group="${group.id}"><button class="barkan-site-tab" type="button" aria-expanded="false" aria-controls="barkan-site-panel-${group.id}">${group.label}${chevron}</button><div class="barkan-site-panel" id="barkan-site-panel-${group.id}" hidden><p class="barkan-site-panel-head">${group.summary}</p><div class="barkan-site-panel-grid">${group.items.map(itemMarkup).join('')}</div></div></div>`).join('');
  const mobileGroups = groups.map(group => `<section class="barkan-site-mobile-group"><h2>${group.label}</h2>${group.items.map(itemMarkup).join('')}</section>`).join('');
  const mobilePrimary = '<a class="barkan-site-mobile-primary" href="/law"><strong>법전</strong><span>서버의 권리·의무·제재 기준</span></a>';

  host.innerHTML = `<nav class="barkan-site-nav" aria-label="주 메뉴"><a class="barkan-site-brand" href="/"><strong>BARKAN</strong><small>ISLANDS</small></a><div class="barkan-site-links" role="menubar">${desktopGroups}</div><a class="barkan-site-direct" href="/law">법전</a><div class="barkan-site-tools"><a class="barkan-site-profile" data-auth-link href="/community/login">로그인</a><button class="barkan-site-menu-toggle" type="button" aria-expanded="false" aria-controls="barkan-site-mobile-menu"><i aria-hidden="true"><span></span><span></span><span></span></i><b>메뉴</b></button></div><div class="barkan-site-mobile-menu" id="barkan-site-mobile-menu" hidden>${mobilePrimary}${mobileGroups}</div></nav>`;

  const groupsEls = [...host.querySelectorAll('.barkan-site-group')];
  const mobileToggle = host.querySelector('.barkan-site-menu-toggle');
  const mobileMenu = host.querySelector('.barkan-site-mobile-menu');
  const closeGroups = () => groupsEls.forEach(group => {
    group.querySelector('.barkan-site-tab').setAttribute('aria-expanded', 'false');
    group.querySelector('.barkan-site-panel').hidden = true;
  });
  const openGroup = group => {
    closeGroups();
    closeMobile();
    group.querySelector('.barkan-site-tab').setAttribute('aria-expanded', 'true');
    group.querySelector('.barkan-site-panel').hidden = false;
  };
  const closeMobile = ({restoreFocus = false} = {}) => {
    mobileMenu.hidden = true;
    mobileToggle.setAttribute('aria-expanded', 'false');
    if (restoreFocus) mobileToggle.focus();
  };
  groupsEls.forEach(group => {
    const tab = group.querySelector('.barkan-site-tab');
    const panel = group.querySelector('.barkan-site-panel');
    tab.addEventListener('click', () => {
      const open = tab.getAttribute('aria-expanded') === 'true';
      if (open) closeGroups();
      else openGroup(group);
    });
    group.addEventListener('mouseenter', () => { if (window.matchMedia('(pointer: fine)').matches) openGroup(group); });
    group.addEventListener('mouseleave', () => { if (window.matchMedia('(pointer: fine)').matches) closeGroups(); });
    panel.addEventListener('click', event => { if (event.target.closest('a')) closeGroups(); });
  });
  mobileToggle.addEventListener('click', () => {
    const open = mobileToggle.getAttribute('aria-expanded') === 'true';
    closeGroups();
    if (open) closeMobile();
    else { mobileToggle.setAttribute('aria-expanded', 'true'); mobileMenu.hidden = false; }
  });
  mobileMenu.addEventListener('click', event => { if (event.target.closest('a')) closeMobile(); });
  document.addEventListener('click', event => {
    if (!event.target.closest('.barkan-site-nav')) { closeGroups(); closeMobile(); }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') { closeGroups(); if (!mobileMenu.hidden) closeMobile({restoreFocus: true}); }
  });

  const currentPath = location.pathname.replace(/\/+$/, '') || '/';
  const allLinks = [...host.querySelectorAll('.barkan-site-direct,.barkan-site-panel-grid a,.barkan-site-mobile-menu a')];
  const currentLinks = allLinks.filter(link => {
    if (link.target === '_blank') return false;
    const path = new URL(link.href, location.origin).pathname.replace(/\/+$/, '') || '/';
    return path === currentPath || (path !== '/' && currentPath.startsWith(`${path}/`));
  });
  currentLinks.sort((a, b) => new URL(b.href, location.origin).pathname.length - new URL(a.href, location.origin).pathname.length)[0]?.setAttribute('aria-current', 'page');
  currentLinks.forEach(link => link.closest('.barkan-site-group')?.classList.add('is-current'));

  fetch('/community/session', {credentials: 'same-origin', cache: 'no-store'})
    .then(response => response.ok ? response.json() : null)
    .then(session => {
      const authLink = host.querySelector('[data-auth-link]');
      if (!authLink || !session?.authenticated) return;
      authLink.href = session.profileUrl || '/community/profile';
      authLink.textContent = '프로필';
      authLink.classList.add('is-profile');
    })
    .catch(() => {});
})();
