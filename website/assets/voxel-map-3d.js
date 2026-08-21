/* Barkan voxel map v2
 *
 * The previous renderer projected one height per column onto a 2D canvas. This
 * renderer consumes the actual runs8 scan and draws real instanced WebGL boxes:
 * every contiguous vertical material run keeps its own height, position and
 * color. There are no canvas shadows or fake side faces.
 */
(() => {
  const canvas = document.querySelector('#voxel-map');
  const viewport = document.querySelector('#map-viewport');
  const plane = document.querySelector('.map-plane');
  const terrain = window.BARKAN_TERRAIN_DATA;
  const mapData = window.BARKAN_MAP_DATA;
  if (!canvas || !viewport || !plane || !terrain || !mapData || !window.THREE || !window.THREE.OrbitControls) return;
  canvas.tabIndex = 0;
  canvas.addEventListener('pointerdown', () => canvas.focus(), { passive: true });
  viewport.addEventListener('pointerdown', () => viewport.focus(), { passive: true });

  const THREE = window.THREE;
  const status = document.querySelector('#map-status');
  const decode = value => {
    const raw = atob(value || '');
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
    return bytes;
  };
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const legend = terrain.legend || [];
  const baseY = 60;
  const townSlugs = { '사막마을': 'desert-town', '스폰도시': 'spawn-city', '상단마을': 'upper-town', '왕도': 'royal-city', '항구': 'harbor' };
  // Invisible technical blocks are useful in-game but should never appear on
  // the public map. Keep this filter at the renderer boundary so old scans
  // and future scans behave identically.
  const hiddenBlocks = new Set(['minecraft:light', 'minecraft:barrier']);
  // The public map is a block-space overview, not an item-model viewer.
  // Thin/partial decorative blocks add a large number of instances while
  // contributing almost no geographic information. Omit them consistently
  // at the renderer boundary; cobweb is deliberately kept as a simple white
  // marker below so webs remain legible without loading their texture.
  const omitSmallBlock = name => {
    const key = blockKey(name);
    if (key === 'cobweb') return false;
    // A grass block is a full terrain cube; only the short/tall grass plants
    // match the broad `grass` family below.
    if (key === 'grass_block') return false;
    return /(?:lantern|torch|wall_torch|sapling|flower|grass|fern|vine|roots|mushroom|kelp|seagrass|rail|chain|fence|gate|pane|bars|candle|sign|banner|button|pressure_plate|carpet|slab|stairs|trapdoor|door|wall$|end_rod|lightning_rod|dripstone)/.test(key);
  };
  const townAreas = new Map((mapData.areas || []).map(area => [area.id, area]));
  const detailRegions = terrain.detailRegions || [];
  const detailRegionFor = id => {
    const area = townAreas.get(id);
    return area ? { x1: area.bounds[0], x2: area.bounds[1], z1: area.bounds[2], z2: area.bounds[3] } : null;
  };
  const inRegion = (x, z, region) => region && x >= region.x1 && x <= region.x2 && z >= region.z1 && z <= region.z2;
  const inRegionWithMargin = (x, z, region, margin) => region
    && x >= region.x1 - margin && x <= region.x2 + margin
    && z >= region.z1 - margin && z <= region.z2 + margin;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  // Textures are exported in sRGB like Minecraft's atlas. Without an sRGB
  // output transform WebGL presents every face noticeably too dark.
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.setClearColor(0x061517, 1);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 1, 40000);
  camera.near = 0.1;
  camera.updateProjectionMatrix();
  const controls = new THREE.OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = true;
  controls.minDistance = 110;
  controls.maxDistance = 22000;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.minPolarAngle = 0.12;
  const moveKeys = new Set();
  const worldUp = new THREE.Vector3(0, 1, 0);
  viewport.addEventListener('pointerleave', () => { moveKeys.clear(); });
  const handleMapKeyDown = event => {
    const key = String(event.key || '').toLowerCase();
    const tag = String(event.target?.tagName || '').toUpperCase();
    const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || event.target?.isContentEditable;
    // This page has no map text fields, so once the user is on the map we
    // accept WASD globally. That avoids browser focus stealing the first key
    // after a click/scroll while still preserving normal text input behavior.
    if (!'wasd'.includes(key) || typing) return;
    event.preventDefault();
    moveKeys.add(key);
    // Apply one step immediately as well as in the animation loop. Browser
    // automation and quick taps can deliver keyup before the next frame;
    // without this, only a physically held key would appear to work.
    if (applyKeyboardPan()) {
      updateScaleLabel();
      scheduleRebuild();
    }
  };
  const handleMapKeyUp = event => {
    const key = String(event.key || '').toLowerCase();
    if ('wasd'.includes(key)) moveKeys.delete(key);
  };
  window.addEventListener('keydown', handleMapKeyDown);
  window.addEventListener('keyup', handleMapKeyUp);
  const applyKeyboardPan = () => {
    if (!moveKeys.size) return false;
    const direction = new THREE.Vector3();
    camera.getWorldDirection(direction);
    direction.y = 0;
    if (direction.lengthSq() < 0.0001) return false;
    direction.normalize();
    const right = new THREE.Vector3().crossVectors(direction, worldUp).normalize();
    const delta = new THREE.Vector3();
    if (moveKeys.has('w')) delta.add(direction);
    if (moveKeys.has('s')) delta.sub(direction);
    if (moveKeys.has('a')) delta.sub(right);
    if (moveKeys.has('d')) delta.add(right);
    if (delta.lengthSq() < 0.0001) return false;
    const speed = clamp(camera.position.distanceTo(controls.target) * 0.012, 2, 80);
    delta.normalize().multiplyScalar(speed);
    camera.position.add(delta);
    controls.target.add(delta);
    return true;
  };
  const scaleLabel = document.querySelector('#map-scale-label');
  const updateScaleLabel = () => {
    if (!scaleLabel) return;
    // Camera units are Minecraft blocks. Keep the label readable while it
    // follows the same distance users are changing with +/− and the wheel.
    const estimate = Math.max(1, camera.position.distanceTo(controls.target) * 0.65);
    const step = estimate < 100 ? 10 : estimate < 1000 ? 50 : estimate < 10000 ? 500 : 1000;
    const blocks = Math.max(step, Math.round(estimate / step) * step);
    scaleLabel.textContent = `약 ${blocks.toLocaleString()} blocks`;
  };

  const world = new THREE.Group();
  const voxelGroup = new THREE.Group();
  // Close-up world tiles live beside the selected-town mesh. Keeping them in
  // their own root lets us evict a tile without rebuilding the expensive
  // overview or the already verified town scan.
  const tileGroup = new THREE.Group();
  tileGroup.name = 'map-detail-tiles';
  const borderGroup = new THREE.Group();
  world.add(voxelGroup, tileGroup, borderGroup);
  scene.add(world);
  // No synthetic ocean plane: water must come from the scanned Minecraft
  // blocks too, otherwise maximum zoom shows a fake flat blue sheet.
  scene.add(new THREE.HemisphereLight(0xc8efe1, 0x1b3430, 1.3));
  const fillLight = new THREE.DirectionalLight(0xffedc3, 0.5);
  fillLight.position.set(420, 900, 260);
  scene.add(fillLight);

  const materialCache = new Map();
  const textureLoader = new THREE.TextureLoader();
  const textureCache = new Map();
  const blockKey = name => String(name || '').replace(/^minecraft:/, '');
  const alphaBlock = name => /(?:leaves|glass|pane|bars|cobweb|lantern|torch|plant|flower|grass|fern|vine|roots|sapling|mushroom|kelp|seagrass|rail|chain|fence|gate|trapdoor|door)/.test(blockKey(name));
  const rgb = hex => new THREE.Color(hex);
  const blockColor = nameRaw => {
    const name = String(nameRaw || '').replace('minecraft:', '');
    if (!name) return '#477967';
    if (/terracotta|concrete|wool|carpet/.test(name)) {
      if (name.includes('white')) return '#d5d8ca';
      if (name.includes('light_gray')) return '#a9b3af';
      if (name.includes('gray')) return '#69777b';
      if (name.includes('black')) return '#2b3033';
      if (name.includes('red')) return '#c95a52';
      if (name.includes('orange')) return '#c87845';
      if (name.includes('yellow')) return '#d6b54c';
      if (name.includes('lime')) return '#75ad52';
      if (name.includes('green')) return '#4f8b64';
      if (name.includes('cyan')) return '#4296a1';
      if (name.includes('light_blue')) return '#6da9c5';
      if (name.includes('blue')) return '#4e79a4';
      if (name.includes('purple')) return '#8b64a3';
      if (name.includes('magenta')) return '#b15a9d';
      if (name.includes('pink')) return '#d78c9d';
      if (name.includes('brown')) return '#8b6049';
      return '#9b6650';
    }
    if (/water|ice|prismarine|coral|kelp|seagrass/.test(name)) return '#3c88a1';
    if (name.includes('snow')) return '#d5e5de';
    if (/red_|crimson|nether|netherrack/.test(name)) return '#a95649';
    if (/purple|purpur|amethyst|chorus/.test(name)) return '#9a72a9';
    if (/sand|sandstone/.test(name)) return '#c5aa6b';
    if (/leaves|moss|grass|azalea|vine|bamboo|fern|sapling/.test(name)) {
      if (name.includes('birch')) return '#9bc47a';
      if (name.includes('jungle')) return '#64a968';
      if (name.includes('spruce')) return '#5b9364';
      if (name.includes('dark_oak')) return '#5b965f';
      return '#78b96d';
    }
    if (name.includes('birch')) return '#b9a874';
    if (name.includes('spruce')) return '#705641';
    if (name.includes('dark_oak')) return '#5d4333';
    if (name.includes('jungle')) return '#9c704f';
    if (name.includes('acacia')) return '#a96f4d';
    if (name.includes('mangrove')) return '#95504a';
    if (/wood|log|planks|shelf|bookshelf|fence|gate|trapdoor/.test(name)) return '#96704d';
    if (/path|dirt|mud|farmland|root/.test(name)) return '#806b4a';
    if (name.includes('gold') || name.includes('hay_block')) return '#d5ae45';
    if (name.includes('copper')) return '#bd7653';
    if (/raw_|iron|ore|diamond|emerald/.test(name)) return '#8d9aa0';
    if (/glass|quartz/.test(name)) return '#c5d3ce';
    if (/gravel|clay/.test(name)) return '#8f8a7c';
    if (name.includes('cactus')) return '#4d8c65';
    if (name.includes('pumpkin')) return '#c8893f';
    if (name.includes('stone_brick')) return '#7c827d';
    if (name.includes('brick')) return '#a36858';
    if (name.includes('diorite')) return '#b3b8af';
    if (name.includes('granite')) return '#a47c68';
    if (name.includes('andesite')) return '#7f8c8b';
    if (name.includes('deepslate')) return '#536267';
    if (name.includes('tuff')) return '#878b7e';
    if (name.includes('cobble')) return '#747b77';
    if (name.includes('basalt')) return '#5f686a';
    if (name.includes('obsidian')) return '#34324c';
    if (/stone/.test(name)) return '#858b87';
    let hash = 0;
    for (let i = 0; i < name.length; i += 1) hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0;
    return ['#6f8e83', '#9a806c', '#6e8795', '#98745e'][Math.abs(hash) % 4];
  };
  const materialFor = (name, variant = 'side') => {
    const key = String(name || '');
    const cacheKey = `${key}|${variant}`;
    if (!materialCache.has(cacheKey)) {
      // Start with the server's palette color, then replace it with the real
      // vanilla block texture as soon as that small PNG arrives.
      const transparent = alphaBlock(key);
      const material = new THREE.MeshLambertMaterial({
        color: rgb(blockColor(key)),
        transparent,
        alphaTest: transparent ? 0.35 : 0,
        side: transparent ? THREE.DoubleSide : THREE.FrontSide,
      });
      materialCache.set(cacheKey, material);
      const textureKey = blockKey(key);
      const fixed = {
        'grass_block|side': 'grass_block_side',
        'grass_block|top': 'grass_block_top',
        'grass_block|bottom': 'dirt',
        'water|side': 'water_still',
        'water|top': 'water_still',
        'water|bottom': 'water_still',
        'lava|side': 'lava_still',
        'lava|top': 'lava_still',
        'lava|bottom': 'lava_still',
        'tall_grass|side': 'tall_grass_bottom',
        'large_fern|side': 'large_fern_bottom',
        // The pack exports lantern as a 16×48 animation strip. The map is
        // static, so use the first 16×16 frame instead of stretching the
        // entire strip across every face.
        'lantern|side': 'lantern_face',
        'lantern|top': 'lantern_face',
        'lantern|bottom': 'lantern_face',
        'soul_lantern|side': 'soul_lantern_face',
        'soul_lantern|top': 'soul_lantern_face',
        'soul_lantern|bottom': 'soul_lantern_face',
      };
      const textureName = fixed[`${textureKey}|${variant}`]
        || (variant !== 'side' ? `${textureKey}_${variant}` : textureKey);
      const applyTexture = loaded => {
        loaded.magFilter = THREE.NearestFilter;
        loaded.minFilter = THREE.NearestFilter;
        loaded.generateMipmaps = false;
        loaded.encoding = THREE.sRGBEncoding;
        material.map = loaded;
        // Vanilla foliage/water textures are grayscale and receive their
        // biome tint in-game. Preserve our server palette for those, while
        // keeping already-colored wood/stone/concrete textures untouched.
        if (!/(grass_block|water|lava|leaves|grass|fern|vine|seagrass|kelp|bamboo|azalea|moss|cactus)/.test(textureKey)) {
          material.color.set(0xffffff);
        }
        material.needsUpdate = true;
      };
      const textureCandidates = () => {
        const candidates = [];
        const add = candidate => { if (candidate && !candidates.includes(candidate)) candidates.push(candidate); };
        add(textureName);
        add(textureKey);
        const suffixes = [
          '_fence_gate', '_pressure_plate', '_wall_hanging_sign', '_hanging_sign', '_wall_sign',
          '_trapdoor', '_button', '_fence', '_carpet', '_stairs', '_slab', '_wall', '_shelf', '_bed', '_door',
        ];
        const base = suffixes.find(suffix => textureKey.endsWith(suffix));
        if (base) {
          const stem = textureKey.slice(0, -base.length);
          add(stem);
          add(`${stem}_planks`);
          add(`${stem}_log`);
          add(`${stem}_block`);
          if (base === '_carpet' || base === '_bed') add(`${stem}_wool`);
        }
        if (textureKey.endsWith('_wood')) {
          const stem = textureKey.slice(0, -5);
          add(`${stem}_log`); add(`${stem}_planks`);
        }
        if (textureKey.endsWith('_stained_glass_pane')) add(textureKey.replace('_pane', ''));
        if (textureKey.endsWith('_banner') || textureKey.endsWith('_wall_banner')) {
          const color = textureKey.replace('_wall_banner', '').replace('_banner', '');
          add(`${color}_wool`); add(`${color}_terracotta`);
        }
        if (textureKey.startsWith('potted_')) add(textureKey.slice(7));
        if (textureKey === 'bamboo') add('bamboo_stalk');
        if (textureKey === 'wheat') add('wheat_stage7');
        if (textureKey === 'smooth_quartz' || textureKey.startsWith('smooth_quartz_')) add('quartz_block_side');
        if (textureKey === 'smooth_sandstone' || textureKey.startsWith('smooth_sandstone_')) add('sandstone');
        if (textureKey === 'smooth_red_sandstone' || textureKey.startsWith('smooth_red_sandstone_')) add('red_sandstone');
        const familyAliases = {
          brick: 'bricks', brick_slab: 'bricks', brick_stairs: 'bricks', brick_wall: 'bricks',
          mud_brick: 'mud_bricks', mud_brick_slab: 'mud_bricks', mud_brick_stairs: 'mud_bricks', mud_brick_wall: 'mud_bricks',
          stone_brick: 'stone_bricks', stone_brick_slab: 'stone_bricks', stone_brick_stairs: 'stone_bricks', stone_brick_wall: 'stone_bricks',
          deepslate_brick: 'deepslate_bricks', deepslate_brick_slab: 'deepslate_bricks', deepslate_brick_stairs: 'deepslate_bricks', deepslate_brick_wall: 'deepslate_bricks',
          deepslate_tile: 'deepslate_tiles', deepslate_tile_slab: 'deepslate_tiles', deepslate_tile_stairs: 'deepslate_tiles', deepslate_tile_wall: 'deepslate_tiles',
          nether_brick: 'nether_bricks', nether_brick_fence: 'nether_bricks', nether_brick_slab: 'nether_bricks', nether_brick_stairs: 'nether_bricks', nether_brick_wall: 'nether_bricks',
          red_nether_brick: 'red_nether_bricks', red_nether_brick_slab: 'red_nether_bricks', red_nether_brick_stairs: 'red_nether_bricks',
          prismarine_brick: 'prismarine_bricks', prismarine_brick_slab: 'prismarine_bricks', prismarine_brick_stairs: 'prismarine_bricks',
          polished_blackstone_brick: 'polished_blackstone_bricks', polished_blackstone_brick_stairs: 'polished_blackstone_bricks',
          tuff_brick: 'tuff_bricks', tuff_brick_wall: 'tuff_bricks',
        };
        add(familyAliases[textureKey]);
        if (textureKey === 'iron_chain') add('chain');
        if (textureKey === 'campfire' || textureKey === 'soul_campfire') add(`${textureKey}_log`);
        if (textureKey === 'decorated_pot') add('terracotta');
        if (textureKey === 'pointed_dripstone') add('pointed_dripstone_up_tip');
        if (textureKey === 'chest' || textureKey === 'ender_chest') add(textureKey === 'ender_chest' ? 'obsidian' : 'barrel_side');
        if (textureKey === 'cartography_table') add('cartography_table_side1');
        if (textureKey === 'furnace' || textureKey === 'blast_furnace' || textureKey === 'smoker') add(`${textureKey}_side`);
        if (textureKey === 'cauldron' || textureKey === 'lava_cauldron' || textureKey === 'water_cauldron') add('cauldron_side');
        if (textureKey === 'cactus') add('cactus_side');
        if (textureKey === 'dirt_path') add('dirt_path_side');
        if (textureKey === 'hay_block') add('hay_block_side');
        if (textureKey === 'podzol') add('podzol_side');
        if (textureKey === 'polished_basalt') add('polished_basalt_side');
        if (textureKey === 'waxed_lightning_rod') add('lightning_rod');
        if (textureKey.startsWith('craftengine:')) { add('stone'); add('smooth_stone'); }
        return candidates;
      };
      const candidates = textureCandidates();
      const loadNext = index => {
        if (index >= candidates.length) return null;
        const candidate = candidates[index];
        return textureLoader.load(`/assets/mc-blocks/${candidate}.png`, applyTexture, undefined, () => loadNext(index + 1));
      };
      const texture = (textureKey === 'water' || textureKey === 'lava') ? null : loadNext(0);
      textureCache.set(key, texture);
    }
    return materialCache.get(cacheKey);
  };

  const clearGroup = group => { while (group.children.length) group.remove(group.children[group.children.length - 1]); };
  const addRecord = (groups, materialName, x, y, z, sx, sy, sz) => {
    const key = materialName || 'minecraft:stone';
    if (hiddenBlocks.has(key) || omitSmallBlock(key)) return;
    let list = groups.get(key);
    if (!list) { list = []; groups.set(key, list); }
    list.push({ x, y, z, sx, sy, sz });
  };
  // Apply the vanilla-style vertical anchor for thin/floor-mounted blocks.
  // Geometry is scaled around its centre, so without this offset a button,
  // plate, carpet, slab, or lantern floats halfway up the block cell.
  const addBlockRecord = (groups, materialName, x, y, z, sx, sy, sz) => {
    const key = blockKey(materialName);
    if (/_button$/.test(key)) y -= 0.43;
    else if (/_pressure_plate$/.test(key)) y -= 0.44;
    else if (/_carpet$/.test(key) || /^(rail|powered_rail|detector_rail|activator_rail)$/.test(key)) y -= 0.46;
    else if (/_slab$/.test(key)) y -= 0.25;
    else if (/^(soul_)?lantern$/.test(key)) y -= 0.19;
    addRecord(groups, materialName, x, y, z, sx, sy, sz);
  };
  const cobwebMaterial = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.86,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  // A non-close map view is a terrain chart, so only a column whose top is
  // plausible terrain participates in the heightfield.  Decorative builds
  // that start at the scan floor and jump to a high roof (the spawn balloon
  // is the obvious example) must not become a long coloured wall.
  const terrainTopNames = new Set([
    'grass_block', 'dirt', 'coarse_dirt', 'podzol', 'mycelium', 'sand', 'red_sand',
    'gravel', 'stone', 'andesite', 'diorite', 'granite', 'deepslate', 'tuff', 'clay',
    'snow', 'snow_block', 'ice', 'packed_ice', 'blue_ice', 'water', 'lava',
    'netherrack', 'basalt', 'smooth_basalt', 'end_stone', 'obsidian', 'prismarine',
    'mud', 'moss_block', 'sculk', 'bedrock', 'soul_sand', 'soul_soil', 'blackstone',
    'calcite',
  ]);
  const isTerrainTop = name => terrainTopNames.has(blockKey(name));
  const buildMeshes = (groups, target) => {
    const matrix = new THREE.Matrix4();
    groups.forEach((records, materialName) => {
      const geometry = geometryFor(materialName);
      // Splitting prevents a single giant instance buffer on large towns.
      for (let start = 0; start < records.length; start += 50000) {
        const chunk = records.slice(start, start + 50000);
        const custom = blockKey(materialName) === 'cobweb';
        const materials = custom ? cobwebMaterial : [
          materialFor(materialName, 'side'), materialFor(materialName, 'side'),
          materialFor(materialName, 'top'), materialFor(materialName, 'bottom'),
          materialFor(materialName, 'side'), materialFor(materialName, 'side'),
        ];
        const mesh = new THREE.InstancedMesh(geometry, materials, chunk.length);
        // Three r128 cannot infer an InstancedMesh bounding volume from the
        // per-instance matrices. Leaving frustum culling enabled therefore
        // drops valid blocks when the camera rotates or pans to an edge.
        mesh.frustumCulled = false;
        mesh.instanceMatrix.setUsage(THREE.StaticDrawUsage);
        chunk.forEach((record, index) => {
          matrix.makeScale(record.sx, record.sy, record.sz);
          matrix.setPosition(record.x, record.y, record.z);
          mesh.setMatrixAt(index, matrix);
        });
        mesh.instanceMatrix.needsUpdate = true;
        target.add(mesh);
      }
    });
  };

  // Non-1:1 views are cartography, not an inventory of stretched Minecraft
  // cubes. Draw a heightfield surface (top faces plus terrain edge walls)
  // instead of a BoxGeometry whose Y scale can turn a balloon into a tower.
  // The close 1:1 shell below remains the only path that renders real cubes.
  const buildSurfaceMesh = (cells, target = voxelGroup) => {
    const grouped = new Map();
    const lookup = new Map();
    cells.forEach(cell => {
      if (!cell || hiddenBlocks.has(cell.materialName) || omitSmallBlock(cell.materialName)) return;
      const list = grouped.get(cell.materialName) || [];
      list.push(cell);
      grouped.set(cell.materialName, list);
      lookup.set(`${cell.x - cell.size / 2}|${cell.z - cell.size / 2}`, cell);
    });
    grouped.forEach((records, materialName) => {
      const positions = [];
      const indices = [];
      const addQuad = (a, b, c, d) => {
        const base = positions.length / 3;
        positions.push(...a, ...b, ...c, ...d);
        indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
      };
      records.forEach(record => {
        const half = record.size / 2;
        const x1 = record.x - half; const x2 = record.x + half;
        const z1 = record.z - half; const z2 = record.z + half;
        const y = record.y;
        const base = Number(record.base ?? baseY);
        // Top face.
        addQuad([x1, y, z1], [x2, y, z1], [x2, y, z2], [x1, y, z2]);
        // Close the heightfield at exposed edges and height changes. These
        // are continuous terrain faces, not individual block sides.
        const neighbours = [
          [x2, z1, x1, z1, x2, z2],
          [x1, z2, x2, z2, x1, z1],
          [x1, z1, x1, z2, x2, z1],
          [x2, z2, x2, z1, x1, z2],
        ];
        neighbours.forEach(([edgeX, edgeZ, ax, az, bx, bz]) => {
          const neighbour = lookup.get(`${Math.round(edgeX)}|${Math.round(edgeZ)}`);
          const neighbourY = neighbour ? neighbour.y : base;
          if (neighbourY >= y - 0.05) return;
          addQuad([ax, y, az], [bx, y, bz], [bx, neighbourY, bz], [ax, neighbourY, az]);
        });
      });
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();
      // Surface LOD is a cartographic heightfield, not a lit pile of block
      // cubes. Use the server palette directly so the overview cannot wash
      // pale under the close-up scene lights; the edge walls and perspective
      // still provide the 3D relief.
      const surfaceColor = rgb(blockColor(materialName));
      // `outputEncoding` expects linear material values. Convert the
      // hand-authored Minecraft palette from sRGB first; otherwise grass,
      // sand and water become a milky white in the overview.
      if (typeof surfaceColor.convertSRGBToLinear === 'function') surfaceColor.convertSRGBToLinear();
      const material = new THREE.MeshBasicMaterial({
        color: surfaceColor,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.frustumCulled = false;
      target.add(mesh);
    });
  };

  const cobwebGeometry = () => {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array([
      -.45, -.45, 0,  .45, -.45, 0,  .45, .45, 0,  -.45, .45, 0,
      0, -.45, -.45,  0, -.45, .45,  0, .45, .45,  0, .45, -.45,
    ]);
    const uvs = new Float32Array([
      0, 0, 1, 0, 1, 1, 0, 1,
      0, 0, 1, 0, 1, 1, 0, 1,
    ]);
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    geometry.setIndex([0, 1, 2, 0, 2, 3, 4, 5, 6, 4, 6, 7]);
    geometry.computeVertexNormals();
    return geometry;
  };
  const geometryCache = new Map();
  const discreteBlock = name => /(?:cobweb|lantern|torch|sapling|flower|grass|fern|vine|roots|mushroom|kelp|seagrass|rail|chain|fence|gate|pane|bars|candle|sign|banner|button|pressure_plate|end_rod|lightning_rod|dripstone)/.test(blockKey(name));
  const geometryFor = name => {
    const key = blockKey(name);
    if (geometryCache.has(key)) return geometryCache.get(key);
    let geometry;
    if (key === 'cobweb') {
      geometry = cobwebGeometry();
    } else {
      geometry = new THREE.BoxGeometry(1, 1, 1);
      const compact = (() => {
        if (/^(soul_)?lantern$/.test(key)) return [.36, .62, .36];
        if (/^(soul_|redstone_)?torch$/.test(key) || /_wall_torch$/.test(key)) return [.2, .7, .2];
        if (/^(oak|spruce|birch|jungle|acacia|dark_oak|mangrove|cherry|bamboo|pale_oak)_sapling$/.test(key) || /^(allium|azure_bluet|blue_orchid|dandelion|poppy|oxeye_daisy|cornflower|lily_of_the_valley|wither_rose|torchflower|pink_petals)$/.test(key)) return [.45, .72, .45];
        if (/^(oak|spruce|birch|jungle|acacia|dark_oak|mangrove|cherry|bamboo|pale_oak)_(fence|fence_gate)$/.test(key) || /_wall$/.test(key)) return [.75, 1, .75];
        if (/^(oak|spruce|birch|jungle|acacia|dark_oak|mangrove|cherry|bamboo|pale_oak)_door$/.test(key) || /_trapdoor$/.test(key)) return [1, 1, .22];
        if (/_pane$/.test(key) || /^(iron_bars|chain)$/.test(key)) return [.16, 1, .16];
        // Buttons and pressure plates are floor-mounted thin blocks, not
        // full cubes. Keep the footprint slightly inset like vanilla.
        if (/_button$/.test(key)) return [.36, .14, .36];
        if (/_pressure_plate$/.test(key)) return [.92, .12, .92];
        if (/_carpet$/.test(key) || /^(rail|powered_rail|detector_rail|activator_rail)$/.test(key)) return [1, .08, 1];
        if (/_slab$/.test(key)) return [1, .5, 1];
        return null;
      })();
      if (compact) geometry.scale(...compact);
    }
    geometryCache.set(key, geometry);
    return geometry;
  };

  const buildOverview = (excludeId = '') => {
    const cells = [];
    const materials = decode(terrain.materials);
    const mask = decode(terrain.mask);
    const heights = decode(terrain.heights);
    const cellSize = Number(terrain.cellSize) || 8;
    const width = Number(terrain.gridWidth) || 0;
    const depth = Number(terrain.gridDepth) || 0;
    const excludedArea = townAreas.get(excludeId);
    const excludedBounds = excludedArea ? excludedArea.bounds : null;
    const excludedMargin = 48;
    for (let j = 0; j < depth; j += 1) {
      for (let i = 0; i < width; i += 1) {
        const index = j * width + i;
        if (!mask[index]) continue;
        const height = (heights[index * 2] | (heights[index * 2 + 1] << 8)) - 128;
        const x = Number(terrain.xOrigin) + i * cellSize;
        const z = Number(terrain.zOrigin) + j * cellSize;
        // Keep the selected town's high-detail scan clean, but do not erase
        // every other town from the island overview. Their lower-resolution
        // terrain cells provide the loading placeholder until a town is
        // focused, so all major settlements remain visible.
        if (excludeId && detailRegions.some(region => region.id === excludeId && inRegion(x + cellSize / 2, z + cellSize / 2, region))) continue;
        if (excludedBounds) {
          const cx = x + cellSize / 2; const cz = z + cellSize / 2;
          if (cx >= excludedBounds[0] - excludedMargin && cx <= excludedBounds[1] + excludedMargin && cz >= excludedBounds[2] - excludedMargin && cz <= excludedBounds[3] + excludedMargin) continue;
        }
        const materialName = legend[materials[index]] || 'minecraft:grass_block';
        // Topdown terrain snapshots also contain the roof of tall decorative
        // models.  Keep those out of every non-1:1 surface view; the exact
        // block shell is available only after the user zooms to 1:1.
        if (height - baseY > 80 && !isTerrainTop(materialName)) continue;
        // A sea/river column has its top exactly at the base Y. Keep a flat
        // water surface there; never manufacture a tall block column.
        if (height <= baseY) {
          if (materialName === 'minecraft:water') {
            cells.push({ materialName, x: x + cellSize / 2, y: baseY + 0.01, z: z + cellSize / 2, size: cellSize });
          }
          continue;
        }
        cells.push({ materialName, x: x + cellSize / 2, y: height + 0.01, z: z + cellSize / 2, size: cellSize });
      }
    }
    buildSurfaceMesh(cells, voxelGroup);
  };

  const buildDetail = (payload, target = voxelGroup) => {
    const groups = new Map();
    const bytes = decode(payload.details);
    const localLegend = payload.legend || [];
    const originX = Number(payload.xOrigin) || 0;
    const originZ = Number(payload.zOrigin) || 0;
    const originY = Number(payload.yOrigin) || 0;
    const floor = Number(payload.surfaceFloor ?? 60);
    // One instance represents one scanned block run at its real X/Z cell.
    // We merge only identical runs; air gaps and material changes remain visible.
    const lod = 1;
    const merged = new Map();
    for (let i = 0; i < Number(payload.count || 0); i += 1) {
      const offset = i * 8;
      const rawX = originX + ((bytes[offset] << 8) | bytes[offset + 1]);
      const rawZ = originZ + ((bytes[offset + 2] << 8) | bytes[offset + 3]);
      const rawY = originY + bytes[offset + 4];
      const length = Math.max(1, bytes[offset + 5]);
      const end = rawY + length;
      if (end <= floor) continue;
      const y = Math.max(rawY, floor);
      const h = end - y;
      const materialName = localLegend[(bytes[offset + 6] << 8) | bytes[offset + 7]] || 'minecraft:stone';
      if (hiddenBlocks.has(materialName) || omitSmallBlock(materialName)) continue;
      const x = Math.floor(rawX / lod) * lod;
      const z = Math.floor(rawZ / lod) * lod;
      if (discreteBlock(materialName)) {
        // A cobweb is a separate marker per block. Never stretch it over a
        // compressed vertical run.
        for (let blockY = y; blockY < end; blockY += 1) {
          const key = `${materialName}|${x}|${z}|${blockY}|1`;
          if (!merged.has(key)) merged.set(key, { materialName, x, z, y: blockY, h: 1 });
        }
      } else {
        // Merge only identical vertical runs in the same LOD cell. Different
        // heights/materials remain separate boxes, so air gaps stay air.
        const key = `${materialName}|${x}|${z}|${y}|${h}`;
        if (!merged.has(key)) merged.set(key, { materialName, x, z, y, h });
      }
    }
    merged.forEach(record => addBlockRecord(groups, record.materialName, record.x + lod / 2, record.y + record.h / 2, record.z + lod / 2, lod, record.h, lod));
    buildMeshes(groups, target);
    return merged.size;
  };

  // Medium zoom LOD: one mesh instance per scanned surface column instead of
  // one instance per material run. A 256×256 tile can contain hundreds of
  // thousands of runs (and therefore expensive matrices/material groups),
  // while its column stream is bounded by 65,536 records. The close view still
  // switches to the exposed 1:1 shell for exact block detail.
  // A surface column is an excellent distant-terrain LOD, but it cannot be
  // used blindly for floating builds. The column scan stores the highest
  // block in a column and a bottom of yMin; a balloon, bridge or airship then
  // becomes a 160-block orange pillar from the ocean floor to its roof. Keep
  // the fast column path for ordinary terrain and reconstruct only suspicious
  // tall/decorative columns from their real runs8 records.
  const buildSurfaceDetail = (payload, target = voxelGroup) => {
    const bytes = decode(payload.columns);
    const localLegend = payload.legend || [];
    const originX = Number(payload.xOrigin) || 0;
    const originZ = Number(payload.zOrigin) || 0;
    const originY = Number(payload.yOrigin) || 0;
    const stride = Number(payload.columnStride) || 10;
    const count = Math.min(Number(payload.columnCount || 0), Math.floor(bytes.length / stride));
    // The first tile appears at a few hundred blocks away. Sampling 2×2 (and
    // 4×4 when farther out) keeps the first frame responsive while the exact
    // shell remains available as the camera approaches the map.
    const distance = camera.position.distanceTo(controls.target);
    const sample = distance > 420 ? 4 : distance > 260 ? 2 : 1;
    const suspicious = new Set();
    const columns = [];
    for (let i = 0; i < count; i += 1) {
      const offset = i * stride;
      const x = originX + ((bytes[offset] << 8) | bytes[offset + 1]);
      const z = originZ + ((bytes[offset + 2] << 8) | bytes[offset + 3]);
      const bottom = originY + bytes[offset + 4];
      const height = Math.max(1, bytes[offset + 5]);
      const topMaterial = localLegend[(bytes[offset + 6] << 8) | bytes[offset + 7]] || 'minecraft:stone';
      const sideMaterial = localLegend[(bytes[offset + 8] << 8) | bytes[offset + 9] ] || topMaterial;
      const key = `${x}|${z}`;
      // A tall non-terrain top is normally a floating decorative model. Do
      // not turn it into a solid column; its exact runs are drawn below.
      if (height > 80 && !isTerrainTop(topMaterial)) suspicious.add(key);
      columns.push({ x, z, bottom, height, topMaterial, sideMaterial, key });
    }

    const cells = [];
    for (const column of columns) {
      if ((column.x - originX) % sample !== 0 || (column.z - originZ) % sample !== 0) continue;
      // Floating decorative columns (notably the balloon) are omitted at
      // non-1:1 zoom. Showing their top as a surface is still misleading;
      // the exact model appears when the user zooms into block view.
      if (suspicious.has(column.key)) continue;
      if (hiddenBlocks.has(column.topMaterial) || omitSmallBlock(column.topMaterial)) continue;
      cells.push({
        materialName: column.topMaterial,
        x: column.x + sample / 2,
        y: column.bottom + column.height + 0.01,
        z: column.z + sample / 2,
        size: sample,
        base: column.bottom,
      });
    }
    buildSurfaceMesh(cells, target);
    return cells.length;
  };

  const buildCloseDetail = (payload, target = voxelGroup) => {
    const groups = new Map();
    const bytes = decode(payload.details);
    const localLegend = payload.legend || [];
    const originX = Number(payload.xOrigin) || 0;
    const originZ = Number(payload.zOrigin) || 0;
    const originY = Number(payload.yOrigin) || 0;
    const floor = Number(payload.surfaceFloor ?? 60);
    const distance = camera.position.distanceTo(controls.target);
    // Keep the close view bounded, but never truncate the scan halfway through
    // a town. The old 420k cap cut off the later X/Z columns (often the lower
    // half of a build) and made structures look exploded.
    const radius = clamp(distance * 2.2, 48, 80);
    const centerX = controls.target.x;
    const centerZ = controls.target.z;
    let blockCount = 0;
    const maxBlocks = 1500000;
    // Keep a real block occupancy map first, then draw only the exposed shell.
    // Rendering every buried block made buildings look like exploded pixels and
    // wasted most of the GPU budget on faces nobody could see.
    const blocks = new Map();
    const keyFor = (x, y, z) => `${x}|${y}|${z}`;
    const columnKeyFor = (x, z) => `${x}|${z}`;
    const runRecords = [];
    const groundedColumns = new Set();
    for (let i = 0; i < Number(payload.count || 0); i += 1) {
      const offset = i * 8;
      const rawX = originX + ((bytes[offset] << 8) | bytes[offset + 1]);
      const rawZ = originZ + ((bytes[offset + 2] << 8) | bytes[offset + 3]);
      if (Math.abs(rawX - centerX) > radius || Math.abs(rawZ - centerZ) > radius) continue;
      const rawY = originY + bytes[offset + 4];
      const length = Math.max(1, bytes[offset + 5]);
      const end = rawY + length;
      const materialName = localLegend[(bytes[offset + 6] << 8) | bytes[offset + 7]] || 'minecraft:stone';
      if (hiddenBlocks.has(materialName) || omitSmallBlock(materialName)) continue;
      runRecords.push({ rawX, rawZ, rawY, end, materialName });
      if (rawY <= floor && end > floor) groundedColumns.add(columnKeyFor(rawX, rawZ));
    }
    runRecords.forEach(run => {
      // A column that reaches the surface is terrain: hide its underground
      // mass. A column with no surface block is floating architecture, so keep
      // its lower pieces (balloon baskets, bridges, suspended docks, etc.).
      const floating = !groundedColumns.has(columnKeyFor(run.rawX, run.rawZ));
      if (run.end <= floor && !floating) return;
      const yStart = floating ? run.rawY : Math.max(run.rawY, floor);
      for (let y = yStart; y < run.end; y += 1) {
        if (blockCount >= maxBlocks) return;
        blocks.set(keyFor(run.rawX, y, run.rawZ), { materialName: run.materialName, x: run.rawX, y, z: run.rawZ });
        blockCount += 1;
      }
    });
    const exposed = ['1,0,0', '-1,0,0', '0,1,0', '0,-1,0', '0,0,1', '0,0,-1'];
    blocks.forEach(block => {
      const visible = exposed.some(offset => {
        const [dx, dy, dz] = offset.split(',').map(Number);
        return !blocks.has(keyFor(block.x + dx, block.y + dy, block.z + dz));
      });
      if (visible) addBlockRecord(groups, block.materialName, block.x + 0.5, block.y + 0.5, block.z + 0.5, 1, 1, 1);
    });
    buildMeshes(groups, target);
    return blockCount;
  };

  // Optional static detail tiles. The generator publishes an index at
  // /assets/map-tiles/index.json and each entry points at a runs8 payload with
  // the same shape as the existing town-detail JSON. The renderer treats the
  // index as an enhancement: if it is absent or a tile is still being scanned,
  // the heightfield/town path continues to work exactly as before.
  const tileState = {
    manifest: null,
    entries: new Map(),
    payloads: new Map(),
    groups: new Map(),
    requests: new Map(),
    generation: 0,
    renderMode: '',
  };
  const clearTileMeshes = () => {
    clearGroup(tileGroup);
    tileState.groups.clear();
    tileState.generation += 1;
    tileState.renderMode = '';
  };
  const floorDiv = (value, size) => Math.floor(Number(value) / Math.max(1, size));
  const tileKey = (tx, tz) => `${tx},${tz}`;
  const tileEntryUrl = entry => {
    const raw = String(entry.url || entry.path || entry.file || '').trim();
    const path = raw || `map-tile-${entry.tx}-${entry.tz}.json`;
    const normalized = path.startsWith('/') ? path : `/assets/map-tiles/${path}`;
    // The manifest timestamp busts a tile cache when a later live scan
    // replaces the same world-space file; the schema version alone would
    // leave a previously visited tile stale in the browser.
    const version = tileState.manifest?.updatedAt || tileState.manifest?.version || '';
    return version ? `${normalized}${normalized.includes('?') ? '&' : '?'}v=${encodeURIComponent(version)}` : normalized;
  };
  const parseTileEntry = (raw, keyHint = '') => {
    const source = raw && typeof raw === 'object' ? { ...raw } : {};
    const key = String(source.key || keyHint || '').replace(/^tile:/, '');
    const keyParts = key.split(/[,:/]/).map(Number);
    let tx = Number(source.tx ?? source.tileX ?? source.gridX);
    let tz = Number(source.tz ?? source.tileZ ?? source.gridZ);
    const tileSize = Number(tileState.manifest?.tileSize) || 256;
    if (!Number.isFinite(tx) && Number.isFinite(keyParts[0])) tx = keyParts[0];
    if (!Number.isFinite(tz) && Number.isFinite(keyParts[1])) tz = keyParts[1];
    if (!Number.isFinite(tx) && Number.isFinite(Number(source.xOrigin))) tx = floorDiv(source.xOrigin, tileSize);
    if (!Number.isFinite(tz) && Number.isFinite(Number(source.zOrigin))) tz = floorDiv(source.zOrigin, tileSize);
    if (!Number.isFinite(tx) && Number.isFinite(Number(source.worldX))) tx = floorDiv(source.worldX, tileSize);
    if (!Number.isFinite(tz) && Number.isFinite(Number(source.worldZ))) tz = floorDiv(source.worldZ, tileSize);
    // A compact manifest may call world-space tile origins x/z. When tx/tz
    // are omitted, values outside the usual tile-index range are interpreted
    // as world coordinates.
    if (Number.isFinite(tx) && Math.abs(tx) > 100 && !source.tx && !source.tileX && !source.gridX) tx = floorDiv(tx, tileSize);
    if (Number.isFinite(tz) && Math.abs(tz) > 100 && !source.tz && !source.tileZ && !source.gridZ) tz = floorDiv(tz, tileSize);
    if (!Number.isFinite(tx) || !Number.isFinite(tz)) return null;
    return { ...source, tx, tz, key: tileKey(tx, tz) };
  };
  const setTileManifest = manifest => {
    if (!manifest || typeof manifest !== 'object') return false;
    tileState.manifest = manifest;
    tileState.entries.clear();
    let records = manifest.tiles;
    if (!Array.isArray(records) && records && typeof records === 'object') {
      records = Object.entries(records).map(([key, value]) => ({ ...(value || {}), key }));
    }
    if (!Array.isArray(records)) records = [];
    records.map(item => parseTileEntry(item)).filter(Boolean).forEach(entry => tileState.entries.set(entry.key, entry));
    return tileState.entries.size > 0;
  };
  const wantedTileEntries = () => {
    if (!tileState.manifest || !tileState.entries.size) return [];
    const tileSize = Number(tileState.manifest.tileSize) || 256;
    const distance = camera.position.distanceTo(controls.target);
    const maxDistance = Number(tileState.manifest.maxDistance ?? 900);
    if (distance > maxDistance) return [];
    const tx = floorDiv(controls.target.x, tileSize);
    const tz = floorDiv(controls.target.z, tileSize);
    // Fetch only the tile under the target first. A 3×3 burst made the first
    // view wait on up to nine large JSON payloads and queued too many meshes;
    // panning requests the next tile incrementally through reconcileTiles.
    const ring = 0;
    const candidates = [];
    for (let dz = -ring; dz <= ring; dz += 1) {
      for (let dx = -ring; dx <= ring; dx += 1) {
        const entry = tileState.entries.get(tileKey(tx + dx, tz + dz));
        if (entry) candidates.push({ entry, distance: Math.abs(dx) + Math.abs(dz) });
      }
    }
    candidates.sort((a, b) => a.distance - b.distance);
    return candidates.slice(0, Math.max(1, Number(tileState.manifest.maxTiles) || 9)).map(item => item.entry);
  };
  const tileStatus = () => {
    let count = 0;
    tileState.payloads.forEach((payload, key) => { if (tileState.groups.has(key)) count += Number(payload.columnCount || payload.count || 0); });
    if (count > 0 && status) status.textContent = `3D TILES · ${count.toLocaleString()} columns`;
  };
  const buildTile = (entry, payload, generation) => {
    if (generation !== tileState.generation || !tileState.entries.has(entry.key)) return;
    const group = new THREE.Group();
    group.name = `tile-${entry.key}`;
    const wantsClose = camera.position.distanceTo(controls.target) < 120;
    const hasColumns = typeof payload.columns === 'string' && Number(payload.columnCount || 0) > 0;
    if (wantsClose) buildCloseDetail(payload, group);
    else if (hasColumns) buildSurfaceDetail(payload, group);
    else buildDetail(payload, group);
    tileGroup.add(group);
    tileState.groups.set(entry.key, group);
    tileStatus();
  };
  const fetchTile = (entry, generation) => {
    if (tileState.payloads.has(entry.key)) {
      buildTile(entry, tileState.payloads.get(entry.key), generation);
      return;
    }
    if (tileState.requests.has(entry.key)) return;
    const request = fetch(tileEntryUrl(entry), { cache: 'force-cache' })
      .then(response => { if (!response.ok) throw new Error(`tile ${entry.key}: ${response.status}`); return response.json(); })
      .then(payload => {
        const normalized = payload?.payload && typeof payload.payload === 'object' ? payload.payload : payload;
        tileState.payloads.set(entry.key, normalized);
        buildTile(entry, normalized, generation);
      })
      .catch(error => console.warn('[barkan map] detail tile unavailable', entry.key, error))
      .finally(() => tileState.requests.delete(entry.key));
    tileState.requests.set(entry.key, request);
  };
  const reconcileTiles = () => {
    if (!tileState.manifest) {
      clearTileMeshes();
      return;
    }
    const wanted = wantedTileEntries();
    const wantedKeys = new Set(wanted.map(entry => entry.key));
    tileState.groups.forEach((group, key) => {
      if (!wantedKeys.has(key)) {
        tileGroup.remove(group);
        tileState.groups.delete(key);
        // Do not retain every tile ever visited during a long map session;
        // the static JSON is cheap to fetch again and GPU/heap memory is not.
        tileState.payloads.delete(key);
      }
    });
    const generation = tileState.generation;
    wanted.forEach(entry => fetchTile(entry, generation));
    tileStatus();
  };
  const loadTileManifest = async () => {
    try {
      const response = await fetch('/assets/map-tiles/index.json', { cache: 'no-store' });
      if (!response.ok) return;
      const manifest = await response.json();
      if (setTileManifest(manifest)) {
        tileState.generation += 1;
        scheduleRebuild();
      }
    } catch (error) {
      // The manifest is deliberately optional while the parallel scan runs.
      console.info('[barkan map] no static detail tile index yet');
    }
  };

  const addLabel = (text, x, z, color) => {
    const canvas2 = document.createElement('canvas');
    canvas2.width = 512; canvas2.height = 128;
    const c = canvas2.getContext('2d');
    c.clearRect(0, 0, 512, 128);
    c.font = '800 48px Barkan, sans-serif';
    c.textAlign = 'center'; c.textBaseline = 'middle';
    c.lineWidth = 12; c.strokeStyle = '#061517'; c.strokeText(text, 256, 64);
    c.fillStyle = color; c.fillText(text, 256, 64);
    const texture = new THREE.CanvasTexture(canvas2);
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: true, depthWrite: false }));
    sprite.position.set(x, 250, z);
    sprite.scale.set(140, 35, 1);
    borderGroup.add(sprite);
  };
  const buildBorders = selectedId => {
    clearGroup(borderGroup);
    (mapData.areas || []).filter(area => area.category !== 'ocean' && Array.isArray(area.polygon) && area.polygon.length >= 3).forEach(area => {
      const segments = [0, ...(area.polygonBreaks || []), area.polygon.length];
      for (let i = 0; i < segments.length - 1; i += 1) {
        const points = area.polygon.slice(segments[i], segments[i + 1]).map(([x, z]) => new THREE.Vector3(x, area.id === selectedId ? 205 : 185, z));
        if (points.length < 3) continue;
        const geometry = new THREE.BufferGeometry().setFromPoints([...points, points[0]]);
        const color = area.id === selectedId ? 0xffe09a : area.category === 'town' ? 0xe8b767 : area.category === 'poi' ? 0xee8e70 : 0x7be0d0;
        borderGroup.add(new THREE.Line(geometry, new THREE.LineBasicMaterial({ color, transparent: true, opacity: area.id === selectedId ? 0.95 : 0.48 }))); 
      }
      if (area.category === 'town' || area.category === 'poi') {
        const [minX, maxX, minZ, maxZ] = area.bounds;
        addLabel(area.name, (minX + maxX) / 2, (minZ + maxZ) / 2, area.category === 'town' ? '#ffe6a4' : '#d8f4ea');
      }
    });
  };

  const fitOverview = () => {
    controls.target.set(0, 80, 0);
    camera.position.set(6400, 6100, 6400);
    controls.minDistance = 180; controls.maxDistance = 22000;
    controls.update();
    updateScaleLabel();
  };
  const zoomBy = factor => {
    const offset = camera.position.clone().sub(controls.target).multiplyScalar(factor);
    camera.position.copy(controls.target).add(offset);
    controls.update();
    updateScaleLabel();
  };
  const orbitBy = (azimuth, polar = 0) => {
    const offset = camera.position.clone().sub(controls.target);
    const spherical = new THREE.Spherical().setFromVector3(offset);
    spherical.theta += azimuth;
    spherical.phi = clamp(spherical.phi + polar, controls.minPolarAngle + 0.02, controls.maxPolarAngle - 0.02);
    offset.setFromSpherical(spherical);
    camera.position.copy(controls.target).add(offset);
    controls.update();
    updateScaleLabel();
  };
  const focusArea = area => {
    if (!area) return;
    const [minX, maxX, minZ, maxZ] = area.bounds;
    const cx = (minX + maxX) / 2; const cz = (minZ + maxZ) / 2;
    const size = Math.max(maxX - minX, maxZ - minZ, 180);
    controls.target.set(cx, 80, cz);
    camera.position.set(cx + size * 0.95, 80 + size * 1.12, cz + size * 0.95);
    // Close enough to see individual 1×1×1 block cubes.
    controls.minDistance = 8;
    controls.maxDistance = Math.max(1200, size * 8);
    controls.update();
  };
  const resize = () => {
    const rect = viewport.getBoundingClientRect();
    const w = Math.max(1, rect.width); const h = Math.max(1, rect.height);
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  };
  const render = () => {
    if (applyKeyboardPan()) {
      updateScaleLabel();
      scheduleRebuild();
    }
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(render);
  };
  let activePayload = null;
  let activeTownId = '';
  let activeMode = 'run';
  let closeCenter = new THREE.Vector3();
  let rebuildTimer = 0;
  let rebuilding = false;
  const rebuildForCamera = force => {
    if ((!activePayload && !tileState.manifest) || rebuilding) return;
    const distance = camera.position.distanceTo(controls.target);
    const wantsClose = distance < 120;
    const movedClose = wantsClose && controls.target.distanceTo(closeCenter) > 24;
    const activeTownRegion = activeTownId ? detailRegionFor(activeTownId) : null;
    // Keep the selected town's real scan while the camera is near its border.
    // Switching to a coarse world tile a few blocks outside the polygon made
    // the settlement suddenly look like a low-resolution rollback.
    const targetInsideTown = inRegionWithMargin(controls.target.x, controls.target.z, activeTownRegion, 640);
    // Keep the verified town scan while the camera is inside that town. Once
    // the user pans out, switch to the static live-world tile at the target so
    // the rest of the island can be explored without loading a monolith.
    const wantsTiles = tileState.manifest && !targetInsideTown && wantedTileEntries().length > 0;
    const wantedTileMode = wantsClose ? 'block' : 'surface';
    if (!force && activeMode === 'tiles' && wantsTiles && tileState.renderMode === wantedTileMode && !movedClose) {
      reconcileTiles();
      return;
    }
    if (wantsTiles) {
      rebuilding = true;
      clearGroup(voxelGroup);
      activeMode = 'tiles';
      clearTileMeshes();
      tileState.renderMode = wantedTileMode;
      reconcileTiles();
      closeCenter.copy(controls.target);
      if (status) status.textContent = '3D TILES · 실측 블록 타일을 불러오는 중…';
      rebuilding = false;
      return;
    }
    // `activeMode` can be `tiles` while the async town payload is already in
    // memory. In that state, entering the town must rebuild its detailed scan
    // instead of returning merely because both views are non-close zoom.
    const hasTownMesh = activeMode === 'run' || activeMode === 'surface' || activeMode === 'block';
    if (!force && activePayload && hasTownMesh && ((wantsClose === (activeMode === 'block')) && !movedClose)) return;
    rebuilding = true;
    if (!activePayload) {
      clearGroup(voxelGroup);
      if (wantsTiles) {
        activeMode = 'tiles';
        // Rebuild cached payloads with the new camera mode (run meshes at
        // medium zoom, exposed 1:1 shell at close zoom).
        clearTileMeshes();
        tileState.renderMode = wantedTileMode;
        reconcileTiles();
      } else {
        clearTileMeshes();
        activeMode = 'overview';
        buildOverview();
      }
      closeCenter.copy(controls.target);
      if (!wantsTiles && status) status.textContent = '3D TERRAIN · 전체 섬 개요';
      rebuilding = false;
      return;
    }
    clearTileMeshes();
    clearGroup(voxelGroup);
    if (!wantsClose) buildOverview(activeTownId);
    if (wantsClose) {
      const count = buildCloseDetail(activePayload);
      if (count > 0) {
        activeMode = 'block';
        closeCenter.copy(controls.target);
        status.textContent = `1:1 BLOCKS · ${activeTownId.toUpperCase()} · ${count.toLocaleString()} blocks`;
      } else {
        const runCount = buildDetail(activePayload);
        activeMode = 'run';
        status.textContent = `3D VOXEL · ${activeTownId.toUpperCase()} · ${runCount.toLocaleString()} meshes`;
      }
    } else {
      const hasColumns = typeof activePayload.columns === 'string' && Number(activePayload.columnCount || 0) > 0;
      if (hasColumns) {
        const surfaceCount = buildSurfaceDetail(activePayload);
        activeMode = 'surface';
        status.textContent = `3D SURFACE · ${activeTownId.toUpperCase()} · ${surfaceCount.toLocaleString()} cells`;
      } else {
        const runCount = buildDetail(activePayload);
        activeMode = 'run';
        status.textContent = `3D VOXEL · ${activeTownId.toUpperCase()} · ${runCount.toLocaleString()} meshes`;
      }
    }
    rebuilding = false;
  };
  const scheduleRebuild = () => {
    if ((!activePayload && !tileState.manifest) || rebuildTimer) return;
    rebuildTimer = window.setTimeout(() => { rebuildTimer = 0; rebuildForCamera(false); }, 140);
  };
  const loadTown = async id => {
    const area = townAreas.get(id);
    const slug = townSlugs[id];
    clearGroup(voxelGroup);
    clearTileMeshes();
    buildBorders(id);
    if (!slug) {
      activePayload = null;
      activeTownId = '';
      activeMode = 'overview';
      buildOverview();
      fitOverview();
      if (tileState.manifest) reconcileTiles();
      return;
    }
    const token = `${id}:${Date.now()}`;
    loadTown.token = token;
    status.textContent = '3D 블록 스캔을 불러오는 중…';
    try {
      const response = await fetch(`/assets/town-detail-${slug}.json?v=4`, { cache: 'no-store' });
      const payload = await response.json();
      if (loadTown.token !== token) return;
      activePayload = payload;
      activeTownId = id;
      activeMode = 'surface';
      buildOverview(id);
      const hasColumns = typeof payload.columns === 'string' && Number(payload.columnCount || 0) > 0;
      const count = hasColumns ? buildSurfaceDetail(payload) : buildDetail(payload);
      closeCenter.copy(controls.target);
      status.textContent = hasColumns
        ? `3D SURFACE · ${id.toUpperCase()} · ${count.toLocaleString()} cells`
        : `3D VOXEL · ${id.toUpperCase()} · ${count.toLocaleString()} meshes`;
    } catch (error) {
      status.textContent = '3D 스캔을 불러오지 못했습니다';
      console.error(error);
    }
    focusArea(area);
  };

  document.querySelectorAll('.map-zoom button').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.zoom === 'in') zoomBy(0.78);
    if (button.dataset.zoom === 'out') zoomBy(1.28);
    if (button.dataset.rotate === 'left') orbitBy(Math.PI / 10);
    if (button.dataset.rotate === 'right') orbitBy(-Math.PI / 10);
    if (button.dataset.pitch === 'up') orbitBy(0, -Math.PI / 14);
    if (button.dataset.pitch === 'down') orbitBy(0, Math.PI / 14);
    if (button.dataset.zoom === 'reset') fitOverview();
    controls.update();
  }));
  document.querySelector('#map-svg')?.style.setProperty('display', 'none');
  buildOverview(); buildBorders('스폰도시'); fitOverview(); resize();
  window.addEventListener('resize', resize, { passive: true });
  controls.addEventListener('change', () => { updateScaleLabel(); scheduleRebuild(); });
  window.addEventListener('barkan-map-state', event => {
    const id = event.detail?.id || '';
    const area = townAreas.get(id);
    buildBorders(id);
    loadTown(id);
    if (area && !townSlugs[id]) focusArea(area);
  });
  render();
  // Tile generation is intentionally asynchronous; the verified town scan is
  // shown immediately while the optional island index is discovered.
  loadTileManifest();
  loadTown('스폰도시');
})();
