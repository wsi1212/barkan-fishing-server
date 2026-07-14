# 바르칸 열도 BGM — Suno 프롬프트 (지역×날씨 풀 매트릭스 v3)

> 방향: **마인크래프트(C418)풍** — 펠트 피아노, 따뜻한 아날로그 신스 패드, 뮤직박스, 글라스벨, 음 사이의 침묵. 오케스트라/민속악기 편성 금지.
> 구성: 지역 8 × 날씨 9(맑음 포함) = 72곡 + 동굴(날씨 무관) + 보스전 2곡 = **총 75개 프롬프트**.
>
> **사용법**: Suno Custom 모드, Instrumental ON, 프롬프트를 Style 칸에.
> **Exclude Styles(공통)**: `vocals, singing, rap, EDM, dubstep, trap, orchestra, epic trailer, drums`
> (★태풍 곡과 보스전 곡만 `drums`를 빼고 제외할 것)
>
> **sounds.json 키 제안**: `music.<지역>.<날씨>` — 지역: spawn/plains/deepforest/desert/oasis/swamp/ice/ocean, 날씨: clear/rain/thunder/typhoon/fog/sandstorm/blizzard/tropicnight/swelter. 동굴=`music.cave`, 보스=`music.boss.imugi`, `music.boss.imugi2`

---

## 1. 스폰마을 (스폰도시 — 항구 마을) `music.spawn.*`

### 1-0. 맑음 (기본)
```
Minimalist ambient video game music like classic sandbox game soundtracks.
Soft felt piano playing a simple wistful melody with lots of space between
notes, warm analog synth pads, faint music-box sparkles, gentle tape warmth.
A quiet fishing harbor at golden hour, wooden docks and drying nets, distant
seagulls, feeling of home. Very slow, dreamy, nostalgic. No drums, no
orchestra, instrumental only, loopable.
```

### 1-1. 비
```
Minimalist ambient game music. Soft felt piano notes falling slowly like
raindrops over warm analog synth pads, faint music-box sparkles. Gentle
steady rain on wooden docks and rooftops of a small fishing harbor, distant
soft thunder, lanterns glowing in the drizzle, gray cozy sky over the sea.
Melancholic but comforting, nostalgic, lots of space between notes. No drums,
instrumental only, loopable.
```

### 1-2. 뇌우
```
Minimalist ambient game music, tense and hushed. Sparse felt piano in a minor
key over a low brooding synth drone, heavy rain and rolling thunder over a
fishing harbor, boats rocking at their moorings, shutters closed, brief
silences before each distant rumble. Cozy dread of watching a storm from
indoors. Restrained, never epic. No drums, instrumental only, loopable.
```

### 1-3. 태풍 (★drums 제외 금지)
```
Dark minimalist ambient game music. Urgent sparse piano notes swallowed by
howling wind, lashing rain over a small harbor, ropes groaning and waves
crashing against the pier, swinging lanterns, deep synth pads swelling like
storm surge, a faint slow heartbeat pulse of low percussion. Hold on and
survive. Still ambient, never orchestral. Instrumental only, loopable.
```

### 1-4. 안개
```
Minimalist ambient game music, muffled and dreamlike. Soft felt piano heard
as if through thick sea fog, blurred warm pads with slow filter movement, a
faint foghorn-like low tone once in a while. A harbor vanishing into white,
half-seen masts and dock posts, damp quiet air, tiny water drips. Mysterious
and gentle. No drums, instrumental only, loopable.
```

### 1-5. 모래바람
```
Minimalist ambient game music. Sparse detuned felt piano half-buried in
gritty dry wind, warm dark synth drone, hissing sand textures rattling the
shutters of a small harbor town, hazy red-tinted air over the docks, sand
blown in from a distant desert. Harsh but hypnotic, strange day in a familiar
place. No drums, instrumental only, loopable.
```

### 1-6. 눈보라
```
Minimalist ambient game music. Fragile music-box and felt piano notes almost
lost in howling icy wind, cold glassy pads, deep freezing drone. Snow burying
the wooden docks of a fishing harbor, frozen ropes, warm lantern light behind
frosted windows, whiteout over the sea. Beautiful and merciless, long empty
silences. No drums, instrumental only, loopable.
```

### 1-7. 열대야
```
Minimalist ambient game music, humid and drowsy. Lazy piano notes with a soft
electric-piano glow, thick slow synth pads like heavy night air over a
harbor, crickets and water lapping between moored hulls, moonlight on warm
waves. A sleepless sticky summer night in a fishing town, calm and a little
restless. No drums, instrumental only, loopable.
```

### 1-8. 땡볕
```
Minimalist ambient game music. Shimmering high synth drone like heat haze
over sun-bleached docks, slow drowsy piano notes that seem to melt, distant
cicada-like buzz, glare bouncing off the water, the whole fishing town dozing
in whatever shade it can find. Bright, dazed, sluggish, waiting for evening.
No drums, instrumental only, loopable.
```

---

## 2. 평원·숲 (본섬 필드) `music.plains.*`

### 2-0. 맑음 (기본)
```
Peaceful minimalist ambient game music. Gentle felt piano and soft warm synth
pads, occasional acoustic guitar harmonics like sunlight through leaves,
sparse notes drifting with long silences, subtle birdsong and soft breeze far
in the background. Wide green meadows by a river, childlike wonder and calm
nostalgia, like wandering an endless open world. No drums, instrumental only,
loopable.
```

### 2-1. 비
```
Peaceful minimalist ambient game music. Soft felt piano like raindrops
pattering on leaves, warm mellow pads, gentle steady rain over green meadows
and light woods, birdsong gone quiet, the smell of wet grass, mist rising
from a river. Melancholic but comforting, cozy gray afternoon in an open
world. No drums, instrumental only, loopable.
```

### 2-2. 뇌우
```
Tense minimalist ambient game music. Sparse minor-key felt piano over a low
brooding drone, heavy rain sweeping across open meadows, thunder echoing off
distant hills, trees shivering, brief silences before each rumble. Small and
exposed under a huge black flickering sky, restrained unease, never epic. No
drums, instrumental only, loopable.
```

### 2-3. 태풍 (★drums 제외 금지)
```
Dark minimalist ambient game music. Urgent sparse piano swallowed by a
howling gale, grass flattened in waves, trees bending and cracking at the
forest edge, driving rain across the fields, deep pads swelling like storm
surge, a faint slow heartbeat pulse of low percussion. Find shelter. Ambient
and raw, never orchestral. Instrumental only, loopable.
```

### 2-4. 안개
```
Minimalist ambient game music, muffled and soft. Felt piano heard through
thick white mist lying over dewy meadows, blurred pads, a lone tree
half-seen, dripping leaves, the river only a sound somewhere in the white.
The familiar field made strange and quiet. Dreamlike, gentle, mysterious. No
drums, instrumental only, loopable.
```

### 2-5. 모래바람
```
Minimalist ambient game music. Detuned sparse piano half-buried in gritty dry
wind, dark warm drone, hissing dust sweeping over browned grass, the meadow
sky turned hazy orange, seeds and leaves rattling past. Harsh, hypnotic,
push forward step by step through a strange dust-choked day. No drums,
instrumental only, loopable.
```

### 2-6. 눈보라
```
Minimalist ambient game music. Fragile music-box notes almost lost in howling
icy wind, cold glassy pads, deep freezing drone, whiteout erasing the meadows
and the treeline, snow piling on fence posts, long empty silences. The green
world gone white and silent. Beautiful and merciless. No drums, instrumental
only, loopable.
```

### 2-7. 열대야
```
Minimalist ambient game music, humid and drowsy. Lazy piano with a soft
electric-piano glow, thick warm night-air pads, a full chorus of crickets and
night insects over dark meadows, fireflies drifting along the river,
moonlight on the grass. Sticky summer night, calm and faintly restless. No
drums, instrumental only, loopable.
```

### 2-8. 땡볕
```
Minimalist ambient game music. Shimmering heat-haze drone over sun-scorched
fields, slow drowsy piano notes that seem to melt, cicada buzz droning far
away, wilting grass and dazzling glare, everything still and waiting for
shade. Bright, dazed, sluggish midsummer noon. No drums, instrumental only,
loopable.
```

---

## 3. 깊은 숲 `music.deepforest.*`

### 3-0. 맑음 (기본)
```
Mysterious minimalist ambient game music. Very sparse soft piano notes with
huge reverb, dark warm synth drone, faint glassy bell tones like fireflies,
slow evolving pads. Hushed and ancient, giant mossy trees and pale light
shafts, a forest that remembers something older than the world. Distant owl,
creaking wood. Dreamlike and reverent, never scary. No drums, instrumental
only, loopable.
```

### 3-1. 비
```
Mysterious minimalist ambient game music. Sparse reverb-heavy piano beneath
rain dripping down through a giant canopy, each drop finding its way from
leaf to leaf, dark warm drone, glassy bell tones, wet moss and deep green
shadow. The ancient forest drinking quietly. Hushed, melancholic, comforting.
No drums, instrumental only, loopable.
```

### 3-2. 뇌우
```
Mysterious minimalist ambient game music, tense and hushed. Minor-key sparse
piano with huge reverb, thunder rolling muffled above the canopy, rain
crashing on leaves far overhead while the forest floor stays dim and
sheltered, brief flashes lighting the mossy giants. Ancient trees unmoved by
the storm. Restrained awe. No drums, instrumental only, loopable.
```

### 3-3. 태풍 (★drums 제외 금지)
```
Dark minimalist ambient game music. Urgent sparse piano beneath a canopy
roaring like the sea, whole giant trees groaning and swaying, branches
cracking somewhere in the dark, driving rain bursting through the leaves,
deep swelling pads, a faint slow heartbeat pulse of low percussion. The old
forest in fury. Ambient, never orchestral. Instrumental only, loopable.
```

### 3-4. 안개
```
Mysterious minimalist ambient game music. Muffled piano notes dissolving into
thick fog between giant mossy trunks, blurred dark pads, glassy tones like
lights that might not be fireflies, shapes half-seen and gone. The deep
forest with its memory drawn close around it. Ghostly but gentle, dreamlike.
No drums, instrumental only, loopable.
```

### 3-5. 모래바람
```
Mysterious minimalist ambient game music. Detuned sparse piano with huge
reverb while gritty dry wind sifts red dust down through the canopy, hissing
sand textures against ancient bark, the green dimmed to haze, leaves
rattling. A desert wind lost in the wrong world. Strange, hypnotic, uneasy
but gentle. No drums, instrumental only, loopable.
```

### 3-6. 눈보라
```
Mysterious minimalist ambient game music. Fragile music-box notes under snow
hissing through the high canopy, boughs sagging white, cold glassy pads and a
deep freezing drone, the ancient forest muffled into total silence between
gusts. Whiteout among giant sleeping trees. Beautiful, solemn, merciless. No
drums, instrumental only, loopable.
```

### 3-7. 열대야
```
Mysterious minimalist ambient game music, humid and dark. Lazy reverb-heavy
piano with a soft electric-piano glow, thick warm night pads, an overwhelming
chorus of night insects deep among mossy giants, fireflies everywhere,
moonlight failing to reach the floor. The old forest breathing in its sleep.
Drowsy, hushed, faintly restless. No drums, instrumental only, loopable.
```

### 3-8. 땡볕
```
Mysterious minimalist ambient game music. Shimmering heat drone pressing down
on the canopy, harsh white light-shafts cutting the dim green, slow drowsy
piano notes melting into huge reverb, cicadas droning through the giant
trees, dry moss and heavy still air. The ancient forest enduring the sun.
Dazed and hushed. No drums, instrumental only, loopable.
```

---

## 4. 사막·붉은사막 (필드) `music.desert.*`

### 4-0. 맑음 (기본)
```
Minimalist ambient game music with a desert mood. Soft felt piano and warm
airy synth pads, a faint breathy flute-like synth note here and there like
heat haze, slow shimmering drone, dry wind whispering far in the background.
Endless red dunes under a huge sky, lonely and majestic, a mirage of an
ancient buried city. No drums, no orchestra, instrumental only, loopable.
```

### 4-1. 비
```
Minimalist ambient game music, quiet wonder. Soft felt piano like the first
raindrops darkening red sand, warm airy pads, gentle rare desert rain hissing
on hot dunes, the smell of wet earth, distant soft thunder over a huge sky.
A once-a-year miracle in a dry land, melancholic and tender. No drums,
instrumental only, loopable.
```

### 4-2. 뇌우
```
Minimalist ambient game music, tense and vast. Sparse minor-key piano over a
low brooding drone, dry lightning flickering over black dunes, thunder
rolling unbroken across an enormous empty sky, wind picking up sand in
gusts, brief total silences. Small and exposed in an endless red waste.
Restrained, never epic. No drums, instrumental only, loopable.
```

### 4-3. 태풍 (★drums 제외 금지)
```
Dark minimalist ambient game music. Urgent sparse piano swallowed by a
screaming sand-laden gale, rain and grit lashing sideways across the dunes,
the sky gone brown-black, deep pads swelling like walls of wind, a faint slow
heartbeat pulse of low percussion. The desert itself airborne. Raw and
ambient, never orchestral. Instrumental only, loopable.
```

### 4-4. 안개
```
Minimalist ambient game music, eerie and soft. Muffled felt piano through a
rare desert fog lying cold on the dunes at dawn, blurred pads, dunes looming
and dissolving like sleeping giants, dew on red sand, utter windless quiet.
The loud empty land gone strange and gentle. Dreamlike. No drums,
instrumental only, loopable.
```

### 4-5. 모래바람 (시그니처)
```
Minimalist ambient game music. Gritty dry wind noise woven through a dark
warm drone, sparse detuned piano notes half-buried in the gale, rattling and
hissing sand textures, a lonely distant flute-like tone appearing and
vanishing in the red murk. Visibility lost in swirling dust, pushing forward
step by step. Harsh, hypnotic. No drums, instrumental only, loopable.
```

### 4-6. 눈보라
```
Minimalist ambient game music, uncanny and beautiful. Fragile music-box notes
in howling icy wind, cold glassy pads over a deep freezing drone, snow — 
impossible snow — whiting out the red dunes, sand and frost hissing together.
A freak storm the desert will talk about for years. Merciless and strange. No
drums, instrumental only, loopable.
```

### 4-7. 열대야
```
Minimalist ambient game music, warm and still. Lazy piano with a soft
electric-piano glow, thick pads like heat still radiating from the sand long
after sunset, a huge starfield over black dunes, faint night insects near
some unseen water. The desert night that never quite cools. Drowsy, calm,
endless. No drums, instrumental only, loopable.
```

### 4-8. 땡볕 (시그니처)
```
Minimalist ambient game music. Shimmering high synth drone like heat haze
rising off red sand, slow drowsy piano notes that seem to melt before they
finish, distant cicada-like buzz, white glare and heavy stillness, dunes
warping in the light. The world bleached and waiting. Dazed, sluggish,
hypnotic. No drums, instrumental only, loopable.
```

---

## 5. 사막마을·오아시스 `music.oasis.*`

### 5-0. 맑음 (기본)
```
Warm minimalist ambient game music, gently uplifting. Soft piano melody a
little brighter and more playful than a desert field theme, warm synth pads,
tiny plucked-string accents like a distant oud heard through a dream, subtle
water shimmer. Date palms and cool spring water in the middle of hot dunes, a
small friendly caravan town at dusk. No drums, instrumental only, loopable.
```

### 5-1. 비
```
Warm minimalist ambient game music, joyful and quiet. Bright soft piano like
rain pattering on palm leaves and tent cloth, warm pads, the whole caravan
town listening to a rare desert rain, ripples spreading across the oasis
pool, children of a blocky world running out to feel it. Tender, grateful,
cozy. No drums, instrumental only, loopable.
```

### 5-2. 뇌우
```
Minimalist ambient game music, hushed and close. Sparse minor-key piano over
a low drone, thunder rolling over a desert town, rain drumming hard on
awnings and mudbrick, palm fronds thrashing, lamplight flickering inside
shuttered stalls, silences between rumbles. Weathering the storm together.
Restrained, cozy dread. No drums, instrumental only, loopable.
```

### 5-3. 태풍 (★drums 제외 금지)
```
Dark minimalist ambient game music. Urgent sparse piano lost in a howling
gale tearing through a caravan town, tents straining and ropes snapping,
sand and rain lashing the oasis water into froth, palms bent double, deep
swelling pads, a faint slow heartbeat pulse of low percussion. Shelter behind
thick walls. Ambient, never orchestral. Instrumental only, loopable.
```

### 5-4. 안개
```
Minimalist ambient game music, soft and strange. Muffled piano through cool
dawn fog pooled over the oasis, blurred warm pads, palm silhouettes floating
in white, the water invisible but heard, tiny plucked-string accents like a
dream not fully remembered. The busy little town silent and ghostly-gentle.
No drums, instrumental only, loopable.
```

### 5-5. 모래바람
```
Minimalist ambient game music. Detuned sparse piano half-buried in gritty
roaring wind, hissing sand pouring over walls and awnings of a shuttered
caravan town, everyone indoors, the oasis pool skinned with dust, a lonely
flute-like tone in the murk. Waiting out the storm over tea. Harsh outside,
warm inside. No drums, instrumental only, loopable.
```

### 5-6. 눈보라
```
Minimalist ambient game music, uncanny. Fragile music-box notes in a howling
icy wind, cold glassy pads, snow settling impossibly on date palms and
mudbrick roofs, the oasis pool steaming against the cold, lamplight glowing
warm through the white. A miracle storm in the desert town. Strange and
beautiful. No drums, instrumental only, loopable.
```

### 5-7. 열대야
```
Minimalist ambient game music, warm and languid. Lazy piano with soft
electric-piano glow, thick humid night pads, crickets around the oasis
water, palm fronds barely stirring, lamplight and low voices from a tea
house, moonlight on the pool. A caravan town that can't sleep and doesn't
mind. No drums, instrumental only, loopable.
```

### 5-8. 땡볕
```
Minimalist ambient game music. Shimmering heat drone over a caravan town at
blinding noon, drowsy melting piano notes, cicada buzz, streets empty and
white with glare, everyone crowded into the palm shade by the cool water. The
oasis earning its name. Dazed, still, grateful for shadow. No drums,
instrumental only, loopable.
```

---

## 6. 늪지대 `music.swamp.*`

### 6-0. 맑음 (기본)
```
Murky minimalist ambient game music. Detuned soft piano notes dripping
slowly, deep humid synth drone, wobbly muted bell tones, faint frog croaks
and insect chirps and slow water bubbles far in the background. Foggy black
still water, mysterious and slightly eerie but cozy in a strange way, like
exploring a swamp at night in a blocky world. No drums, instrumental only,
loopable.
```

### 6-1. 비
```
Murky minimalist ambient game music. Detuned piano like rain dimpling black
still water, deep humid drone, wobbly bell tones, steady rain hissing on
reeds and lily pads, frogs delighted and loud, everything dripping. The swamp
in its favorite weather. Damp, cozy, gently eerie. No drums, instrumental
only, loopable.
```

### 6-2. 뇌우
```
Murky minimalist ambient game music, tense. Sparse minor-key detuned piano
over a deep brooding drone, thunder rolling across flat black water, rain
hammering the reeds, frogs gone silent, dead trees lit white by distant
flashes, slow bubbles rising between rumbles. The swamp holding its breath.
Restrained unease. No drums, instrumental only, loopable.
```

### 6-3. 태풍 (★drums 제외 금지)
```
Dark minimalist ambient game music. Urgent detuned piano swallowed by wind
screaming over open marsh, reeds flattened, black water whipped into chop,
dead trees groaning and snapping, driving rain, deep swelling pads, a faint
slow heartbeat pulse of low percussion. Nowhere to hide in the flat wet
waste. Ambient, raw. Instrumental only, loopable.
```

### 6-4. 안개
```
Murky minimalist ambient game music, thick and blind. Muffled detuned piano
in fog so dense the water and air trade places, blurred humid pads, a frog
croak with no direction, slow drips, shapes of dead trees appearing an arm's
length away. The swamp's own weather, doubled. Dreamlike, eerie, gentle. No
drums, instrumental only, loopable.
```

### 6-5. 모래바람
```
Murky minimalist ambient game music, strange. Detuned piano half-buried in a
gritty dry gale rattling through brittle reeds, dust skinning the black
water gray, humid drone gone parched, insects silenced by the hiss of sand.
A desert wind trespassing in the wetland. Wrong and hypnotic. No drums,
instrumental only, loopable.
```

### 6-6. 눈보라
```
Murky minimalist ambient game music, frozen. Fragile music-box notes in
howling icy wind, the black water skimmed with ice, snow hissing into reeds,
cold glassy pads over a deep freezing drone, frogs and insects utterly
silent under the white. The swamp stopped mid-breath. Merciless, still,
strange. No drums, instrumental only, loopable.
```

### 6-7. 열대야 (시그니처)
```
Murky minimalist ambient game music, thick and alive. Lazy detuned piano with
soft electric-piano glow, heavy humid night pads, a deafening happy chorus of
frogs and night insects over warm black water, fireflies tangled in the
reeds, moon smeared across the surface. The swamp's festival night. Drowsy,
teeming, cozy-eerie. No drums, instrumental only, loopable.
```

### 6-8. 땡볕
```
Murky minimalist ambient game music. Shimmering heat drone over stagnant
water steaming in the glare, slow melting detuned piano, cicada buzz thick as
the air, mud cracking at the edges, everything green and rotten and dazzling.
The swamp stewing at noon. Sluggish, heavy, hypnotic. No drums, instrumental
only, loopable.
```

---

## 7. 얼음지형 (설원 섬 — 추가 예정) `music.ice.*`

### 7-0. 맑음 (기본)
```
Frozen minimalist ambient game music. Fragile music-box and celesta notes
like falling snowflakes, icy glassy synth pads, soft deep drone, huge cold
reverb, faint arctic wind far away. Crystalline and desolate but achingly
beautiful, aurora shimmering over an endless ice field, held-breath silence
between notes. Nostalgic and pure. No drums, instrumental only, loopable.
```

### 7-1. 비
```
Frozen minimalist ambient game music. Fragile celesta and piano notes like
freezing rain ticking on ice, glassy pads, every surface slowly glazing over,
icicles lengthening drip by drip, gray sky pressing low on the white field.
Cold rain in a colder land, delicate and melancholy. No drums, instrumental
only, loopable.
```

### 7-2. 뇌우
```
Frozen minimalist ambient game music, rare and ominous. Sparse minor-key
piano over a deep freezing drone, thundersnow rumbling across the ice field,
flashes lighting the white from inside the clouds, wind-driven sleet, huge
cold reverb between rumbles. A storm that shouldn't exist here. Restrained
awe. No drums, instrumental only, loopable.
```

### 7-3. 태풍 (★drums 제외 금지)
```
Dark frozen minimalist ambient game music. Urgent fragile notes swallowed by
a polar gale, rain and ice lashing sideways across the field, the aurora
buried in racing black cloud, deep pads swelling like pressure ridges
grinding, a faint slow heartbeat pulse of low percussion. Survive the white
roar. Ambient, raw. Instrumental only, loopable.
```

### 7-4. 안개
```
Frozen minimalist ambient game music, ghostly. Muffled celesta through ice
fog and diamond dust glittering in dead-still air, blurred glassy pads, the
horizon erased, sky and snow the same white, each footstep-crunch swallowed
whole. A world of pure pale silence. Dreamlike, pristine, uncanny. No drums,
instrumental only, loopable.
```

### 7-5. 모래바람
```
Frozen minimalist ambient game music, strange. Detuned fragile notes in a
gritty scouring wind, dry grit and old hard snow hissing together across
blue ice, the white field stained faintly red with dust carried from another
land, glassy drone gone raspy. A desert's breath on the glacier. Wrong,
hypnotic. No drums, instrumental only, loopable.
```

### 7-6. 눈보라 (시그니처)
```
Blizzard minimalist ambient game music. Howling icy wind in the background,
fragile music-box notes almost lost in the storm, cold glassy pads, deep
freezing drone, long empty silences. Whiteout — beautiful and merciless, numb
and quiet at the same time, seeking shelter in an endless snowfield. No
drums, instrumental only, loopable.
```

### 7-7. 열대야
```
Frozen minimalist ambient game music, eerie thaw. Lazy warm electric-piano
notes over glassy pads, an impossibly warm night on the ice, meltwater
dripping and trickling everywhere in the dark, fog steaming off the field,
the aurora blazing overhead as the glacier quietly weeps. Beautiful and
wrong. Drowsy, uncanny. No drums, instrumental only, loopable.
```

### 7-8. 땡볕
```
Frozen minimalist ambient game music. Shimmering high drone like blinding
glare off endless ice, slow melting celesta notes, drips quickening into
rivulets, the whole field one white dazzle under a merciless sun, snow-blind
stillness. The frozen world squinting. Dazed, radiant, sluggish. No drums,
instrumental only, loopable.
```

---

## 8. 대양 (항해·먼 바다) `music.ocean.*`

### 8-0. 맑음 (기본)
```
Vast open ocean minimalist ambient. Very slow deep synth pad swells like the
breathing of the sea, sparse high piano notes like light on water, low
sub-bass hum of the deep far below, huge empty reverb, a faint distant
whale-like tone once in a while. Nothing but horizon in every direction, a
tiny boat on an enormous ancient ocean, and the feeling that something vast
sleeps beneath. No drums, instrumental only, loopable.
```

### 8-1. 비
```
Vast open ocean minimalist ambient. Sparse high piano like rain stippling a
gray sea to the horizon, slow deep pad swells, the hiss of rainfall on water
all around the little boat, no land, no line between sea and sky, sub-bass
hum of the deep below. Utterly alone in the soft gray. Melancholic, calm. No
drums, instrumental only, loopable.
```

### 8-2. 뇌우
```
Vast open ocean minimalist ambient, tense. Minor-key sparse piano over a
brooding sub-bass drone, thunder rolling across open water with nothing to
stop it, rain hammering the deck, swells growing, lightning doubling itself
on the black sea, silences that feel like held breath. Small boat, huge sky.
Restrained dread. No drums, instrumental only, loopable.
```

### 8-3. 태풍 (★drums 제외 금지)
```
Dark open ocean minimalist ambient. Urgent sparse piano lost in a full gale,
mountainous waves, wind screaming through rigging, the boat climbing and
falling, deep pads swelling and crashing like the storm surge itself, a slow
heartbeat pulse of low percussion like a pounding hull. The sea trying to
take you. Ambient, raw, never orchestral. Instrumental only, loopable.
```

### 8-4. 안개
```
Vast open ocean minimalist ambient, blind and still. Muffled piano through
fog lying flat on a windless sea, blurred pads, a foghorn-like low tone
answered by nothing, water lapping the hull the only proof of the world,
sub-bass hum of the deep beneath the white. Adrift inside a cloud. Dreamlike,
hushed, uncanny. No drums, instrumental only, loopable.
```

### 8-5. 모래바람
```
Vast open ocean minimalist ambient, strange. Sparse detuned piano in a dry
gritty wind blown far out to sea, red desert dust hazing the sun and dusting
the deck and the swells, hissing grit in the rigging, deep pad swells rolling
on beneath the murk. The desert crossing the water. Wrong and hypnotic. No
drums, instrumental only, loopable.
```

### 8-6. 눈보라
```
Vast open ocean minimalist ambient, frozen. Fragile music-box notes torn by
howling icy wind over black water, snow vanishing into the swells by the
ton, ice glazing the rigging, cold glassy pads over a deep freezing sub-bass
drone. White chaos above, black deep below, tiny boat between. Merciless,
awesome. No drums, instrumental only, loopable.
```

### 8-7. 열대야
```
Vast open ocean minimalist ambient, warm and still. Lazy electric-piano notes
over slow glassy swells, thick humid night pads, a dead-calm tropical sea
under a huge moon, the boat barely rocking, phosphorescence stirring in the
wake, warm air that never cools. Becalmed on a breathing sea. Drowsy,
endless. No drums, instrumental only, loopable.
```

### 8-8. 땡볕
```
Vast open ocean minimalist ambient. Shimmering heat drone over a glassy
windless sea, slow melting piano notes, blinding glare doubled by the water,
the sail hanging dead, tar softening in the deck seams, the horizon warping.
The doldrums at merciless noon. Dazed, becalmed, hypnotic. No drums,
instrumental only, loopable.
```

---

## 9. 동굴 (물보라 동굴·광산 — 날씨 무관) `music.cave`

지상 곡을 **Cover 기능**에 넣고 이 스타일로 리메이크하면 진짜 "위 세상 곡의 메아리"가 됨.

```
Deep cave minimalist ambient game music. Sparse lonely piano notes drenched
in enormous cavernous reverb, low rumbling drone, resonant glassy tones like
glowing crystals, water droplets echoing in darkness, a faint half-remembered
warm melody drifting down from the surface world as if heard through stone.
Extremely slow and quiet, subterranean awe, wonder and slight unease like
classic sandbox game cave music. No drums, instrumental only, loopable.
```

---

## 10. 보스전 — 이무기 (★drums 제외 금지) `music.boss.imugi`

```
Dark intense ambient-electronic boss battle music for a blocky adventure game.
Ominous deep synth bass pulse, tense evolving pads, pounding heavy toms and
deep taiko-like drums, sharp metallic gong accents, a wailing distant
flute-like lead hinting at Korean traditional sound, dissonant piano stabs
with big reverb. Driving and relentless but not orchestral, a mythic
serpent-dragon rising from a storming abyss, dread and awe. Instrumental,
loopable.
```

### 10b. 최후반 페이즈 `music.boss.imugi2`

```
Final phase of a dark ambient-electronic boss theme. Faster and more
desperate: throbbing synth bass, hammering deep drums and metallic gong hits,
screaming distorted flute-like lead with Korean traditional color, tense
string-like synth tremolo, then brief openings where a fragile sad piano
melody breaks through the chaos — the dying memory of an ancient god-fish.
Overwhelming, tragic, climactic. Instrumental, loopable.
```

---

## 제작 팁

- **75곡 다 뽑지 말고 우선순위**: 각 지역 맑음 8곡 → 비/뇌우/안개(자주 뜨는 날씨) → 시그니처 조합(사막×모래바람·땡볕, 얼음×눈보라, 늪×열대야) → 나머지 희귀 조합은 필요할 때.
- **일관성**: 지역 맑음 곡을 먼저 뽑고, 같은 지역의 날씨 변주는 그 곡을 **Cover**에 넣고 날씨 프롬프트로 리메이크 → 같은 멜로디의 날씨 버전이 되어 인게임 전환이 자연스러움.
- **결과가 화려하면** Exclude에 `cinematic` 추가, **너무 밋밋하면** `lots of space between notes`를 빼기.
- **루프/변환**: `ffmpeg -i in.mp3 -af "afade=t=in:d=1,afade=t=out:st=<끝-2>:d=2" -c:a libvorbis -q:a 5 out.ogg`
- **등록**: `assets/barkan/sounds.json`에 위 키 스킴대로 등록 (weather ogg 파이프라인 그대로).
- **인게임 훅**: RegionTracker 진입/이탈 + WeatherManager 날씨 변경 이벤트에서 `stopsound` → `playsound barkan:music.<지역>.<날씨>` 하는 BgmManager 신설 필요. music 카테고리로 재생하면 유저 음악 슬라이더로 조절 가능.
