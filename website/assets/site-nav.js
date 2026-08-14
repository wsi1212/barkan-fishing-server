(() => {
  let host = document.querySelector('[data-site-nav]');
  if (!host) {
    const legacyNav = document.querySelector('nav.nav[aria-label="주 메뉴"], nav.nav');
    if (!legacyNav) return;
    host = document.createElement('div');
    host.dataset.siteNav = '';
    legacyNav.replaceWith(host);
  }

  if (!document.getElementById('barkan-site-nav-style')) {
    const style = document.createElement('style');
    style.id = 'barkan-site-nav-style';
    style.textContent = `
      .barkan-site-nav{--nav-text:#e8eee4;--nav-muted:#a7bbb1;--nav-faint:#769289;--nav-accent:#d6a05c;--nav-line:rgba(211,231,218,.23);--nav-soft-line:rgba(211,231,218,.13);position:relative;z-index:30;display:flex;height:72px;align-items:center;justify-content:space-between;border-bottom:1px solid var(--nav-line);font-family:Barkan,"Barkan Aggro","Apple SD Gothic Neo","Noto Sans KR",sans-serif}
      .barkan-site-brand{line-height:1;color:inherit;text-decoration:none}.barkan-site-brand strong{display:block;font-size:20px;font-weight:800;letter-spacing:.15em}.barkan-site-brand small{display:block;margin-top:7px;color:var(--nav-accent);font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:8px;font-weight:700;letter-spacing:.22em}
      .barkan-site-tools{display:flex;align-items:center;gap:10px}.barkan-site-profile{display:inline-flex;min-height:36px;align-items:center;padding:7px 12px;border:1px solid var(--nav-line);color:var(--nav-text);font-size:12px;text-decoration:none}.barkan-site-profile:hover,.barkan-site-profile:focus-visible,.barkan-site-profile.is-profile{border-color:var(--nav-accent);color:var(--nav-accent)}
      .barkan-site-menu-toggle{display:inline-flex;min-height:36px;align-items:center;gap:9px;padding:7px 11px;border:1px solid var(--nav-line);background:rgba(8,21,22,.3);color:var(--nav-text);font:500 12px Barkan,"Barkan Aggro","Apple SD Gothic Neo","Noto Sans KR",sans-serif;cursor:pointer}.barkan-site-menu-toggle:hover,.barkan-site-menu-toggle:focus-visible,.barkan-site-menu-toggle[aria-expanded="true"]{border-color:var(--nav-accent);color:var(--nav-accent)}.barkan-site-menu-toggle i{display:grid;gap:3px;width:15px}.barkan-site-menu-toggle i span{display:block;height:1px;background:currentColor}
      .barkan-site-menu{position:absolute;z-index:20;top:calc(100% + 12px);right:0;width:min(390px,calc(100vw - 30px));padding:18px;border:1px solid var(--nav-line);background:rgba(7,24,24,.97);box-shadow:0 18px 45px rgba(0,0,0,.34);backdrop-filter:blur(16px)}.barkan-site-menu[hidden]{display:none}.barkan-site-menu-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;border-top:1px solid var(--nav-soft-line);border-left:1px solid var(--nav-soft-line)}.barkan-site-menu-grid a{display:flex;min-height:48px;align-items:center;padding:12px;border-right:1px solid var(--nav-soft-line);border-bottom:1px solid var(--nav-soft-line);color:var(--nav-muted);font-size:13px;text-decoration:none}.barkan-site-menu-grid a:hover,.barkan-site-menu-grid a:focus-visible,.barkan-site-menu-grid a[aria-current="page"]{background:rgba(35,91,78,.34);color:var(--nav-accent)}.barkan-site-menu-foot{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:14px;color:var(--nav-faint);font:9px/1.4 ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;letter-spacing:.08em}.barkan-site-menu-foot a{color:var(--nav-accent);text-decoration:none}
      @media(max-width:720px){.barkan-site-nav{height:72px}.barkan-site-tools{gap:6px}.barkan-site-profile{padding:7px 9px;font-size:11px}.barkan-site-menu-toggle{padding:7px 9px}.barkan-site-menu{right:-1px}}
      @media(prefers-reduced-motion:reduce){.barkan-site-menu-toggle{transition:none}}
    `;
    document.head.append(style);
  }

  host.innerHTML = `<nav class="barkan-site-nav" aria-label="주 메뉴">
    <a class="barkan-site-brand" href="/"><strong>BARKAN</strong><small>ISLANDS</small></a>
    <div class="barkan-site-tools">
      <a class="barkan-site-profile" data-auth-link href="/community/login">로그인</a>
      <button class="barkan-site-menu-toggle" type="button" aria-expanded="false" aria-controls="barkan-site-menu"><i aria-hidden="true"><span></span><span></span><span></span></i><b>메뉴</b></button>
    </div>
    <div class="barkan-site-menu" id="barkan-site-menu" hidden>
      <nav class="barkan-site-menu-grid" aria-label="전체 메뉴">
        <a href="/#world">세계</a><a href="/wiki/start">시작하기</a><a href="/wiki">위키</a><a href="/dex">도감</a><a href="/gear">장비</a><a href="/catalog">재료·채집</a><a href="/ranking">랭킹</a><a href="/community">커뮤니티</a><a href="https://discord.gg/fWVGGEbBsd" target="_blank" rel="noopener noreferrer">디스코드</a><a href="/vip/">상점</a>
      </nav>
      <div class="barkan-site-menu-foot"><span>JAVA + BEDROCK · 1.21.4 - 1.26.2</span><a href="mailto:wsiwsiwsi123@gmail.com">문의</a></div>
    </div>
  </nav>`;

  const menuToggle = host.querySelector('.barkan-site-menu-toggle');
  const siteMenu = host.querySelector('.barkan-site-menu');
  const closeMenu = ({restoreFocus = false} = {}) => {
    siteMenu.hidden = true;
    menuToggle.setAttribute('aria-expanded', 'false');
    if (restoreFocus) menuToggle.focus();
  };

  menuToggle.addEventListener('click', () => {
    const open = menuToggle.getAttribute('aria-expanded') === 'true';
    menuToggle.setAttribute('aria-expanded', String(!open));
    siteMenu.hidden = open;
  });
  siteMenu.addEventListener('click', event => {
    if (event.target.closest('a')) closeMenu();
  });
  document.addEventListener('click', event => {
    if (!siteMenu.hidden && !event.target.closest('.barkan-site-nav')) closeMenu();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !siteMenu.hidden) closeMenu({restoreFocus: true});
  });

  const currentPath = location.pathname.replace(/\/+$/, '') || '/';
  const currentLinks = [...siteMenu.querySelectorAll('a')].filter(link => {
    const path = new URL(link.href, location.origin).pathname.replace(/\/+$/, '') || '/';
    return path === currentPath || (path !== '/' && currentPath.startsWith(`${path}/`));
  });
  currentLinks.sort((a, b) => new URL(b.href, location.origin).pathname.length - new URL(a.href, location.origin).pathname.length)[0]?.setAttribute('aria-current', 'page');

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
