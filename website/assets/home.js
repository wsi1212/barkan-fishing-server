(() => {
  const copyButton = document.querySelector('[data-server]');
  copyButton?.addEventListener('click', async () => { try { await navigator.clipboard.writeText(copyButton.dataset.server); copyButton.textContent = '복사됨'; setTimeout(() => { copyButton.textContent = '서버 주소 복사'; }, 1600); } catch { copyButton.textContent = copyButton.dataset.server; } });
  const systems = [
    {kicker:'Built for the catch',title:'신기루<br>낚싯대',description:'낚싯대와 부품을 조합하고 강화해, 내가 노리는 물고기에 맞는 장비를 완성하세요.',href:'/gear',link:'장비 살펴보기 ↗'},
    {kicker:'Dive deeper',title:'심해교역<br>작살',description:'수영과 전투 감각을 더한 작살 사냥. 바다 깊은 곳으로 직접 들어가 사냥하세요.',href:'/gear',link:'장비 살펴보기 ↗'},
    {kicker:'Kitchen to table',title:'잡은 물고기는<br>한 접시의 요리',description:'요리를 먹어 버프를 받고, 필요한 곳에 제출하고, 완성품으로 판매할 수도 있습니다.',href:'/wiki',link:'요리 시스템 보기 ↗'},
    {kicker:'A living harbor',title:'항구의 사람들은<br>각자 할 일이 있다',description:'길잡이부터 대장간, 상점, 판매와 여관까지. NPC마다 바르칸 생활의 다음 목적지가 있습니다.',href:'/wiki/start',link:'시작 안내 보기 ↗'},
    {kicker:'Make a crew',title:'혼자 만든 섬도<br>함께하면 길드가 된다',description:'마음 맞는 친구와 길드 섬을 만들고, 기여와 생활 기반을 함께 키워 보세요.',href:'/wiki',link:'위키에서 보기 ↗'},
    {kicker:'Beyond the sea',title:'낚시만 해서는<br>못 얻는 것들',description:'광질과 채집, 특수작물로 다른 재료를 모으고 섬에서 나만의 생산 루트를 만드세요.',href:'/catalog',link:'재료 살펴보기 ↗'},
    {kicker:'After dark',title:'항구의 밤엔<br>한 판 더 걸어본다',description:'카지노에서 손에 땀을 쥐는 한 판. 모험의 쉬는 시간도 바르칸답게 즐겨 보세요.',href:'/wiki',link:'위키에서 보기 ↗'}
  ];
  const tabs = [...document.querySelectorAll('.system-tab')];
  const view = document.querySelector('#system-view');
  const artViewport = document.querySelector('#system-art-viewport');
  const artRail = document.querySelector('#system-art-rail');
  const kicker = document.querySelector('#system-kicker');
  const title = document.querySelector('#system-title');
  const description = document.querySelector('#system-description');
  const link = document.querySelector('#system-link');
  const controls = [...document.querySelectorAll('.system-control')];
  let active = 0;
  let copyTimer;
  const setSystem = (index) => { active = (index + systems.length) % systems.length; const system = systems[active]; tabs.forEach((tab, i) => tab.setAttribute('aria-selected', String(i === active))); artRail.style.transform = `translate3d(${-active * 100}%,0,0)`; view.classList.add('is-changing'); clearTimeout(copyTimer); copyTimer = setTimeout(() => { kicker.textContent = system.kicker; title.innerHTML = system.title; description.textContent = system.description; link.href = system.href; link.textContent = system.link; view.classList.remove('is-changing'); }, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 170); };
  const moveSystem = (direction) => setSystem(active + direction);
  tabs.forEach((tab, index) => { tab.addEventListener('click', () => setSystem(index)); tab.addEventListener('keydown', (event) => { if (event.key === 'ArrowDown' || event.key === 'ArrowRight') { event.preventDefault(); const next = (index + 1) % tabs.length; tabs[next].focus(); setSystem(next); } if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') { event.preventDefault(); const previous = (index - 1 + tabs.length) % tabs.length; tabs[previous].focus(); setSystem(previous); } }); });
  controls.forEach((control) => control.addEventListener('click', () => moveSystem(Number(control.dataset.direction))));
  view?.addEventListener('keydown', (event) => { if (event.key === 'ArrowRight' || event.key === 'ArrowDown') { event.preventDefault(); moveSystem(1); } if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') { event.preventDefault(); moveSystem(-1); } });
  let swipeStartX = null;
  artViewport?.addEventListener('pointerdown', (event) => { swipeStartX = event.clientX; });
  artViewport?.addEventListener('pointerup', (event) => { if (swipeStartX === null) return; const distance = event.clientX - swipeStartX; if (Math.abs(distance) > 44) moveSystem(distance < 0 ? 1 : -1); swipeStartX = null; });
})();
