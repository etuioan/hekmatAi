// Brücke zwischen dem Python-Adapter `hekmatki.adapters.minecraft` und einem Minecraft-Server.
//
// Die Brücke ist ein Spieler-Client (Mineflayer). Sie liest Befehle als JSON-Zeilen von stdin
// und antwortet mit einer JSON-Zeile auf stdout:
//   {"op": "reset", "seed": 7}   neue Runde an einem neuen Ort
//   {"op": "step", "action": 3}  eine Handlung ausführen
//   mit "record": true kommt zusätzlich "scene" (ein Bild der Lage für die Wiedergabe)
//   {"op": "close"}              beenden
// Antwort: {"inner": [Zahlen], "advancements": [neue Fortschritte, z. B. "minecraft:story/mine_stone"],
//           "dead": bool}
// oder bei einem Fehler {"error": "..."}.
//
// Die Brücke kennt Minecraft, der Agent nie: Sie gibt nur Zahlen weiter. Was die Zahlen
// bedeuten, steht in LAYOUT; der Python-Adapter mischt sie, bevor der Agent sie sieht.

'use strict'

// stdout gehört allein dem Protokoll. Was Bibliotheken ausgeben, geht nach stderr.
const send = message => process.stdout.write(JSON.stringify(message) + '\n')
console.log = console.info = console.warn = (...parts) => process.stderr.write(parts.join(' ') + '\n')

const readline = require('node:readline')
const mineflayer = require('mineflayer')
const { Vec3 } = require('vec3')

const VIEW = 5 // Breite und Tiefe des Würfels um die Figur
const LAYERS = [-1, 0, 1] // unter den Füßen, Füße, Kopf
const REACH = 4.5 // so weit reicht ein Spieler im Überlebensmodus
const START_ATTEMPTS = 8 // so oft sucht `reset` einen Startplatz an Land mit Bäumen
const SCENE = 15 // Breite des Ausschnitts für die Wiedergabe (nur für die Seite)
const MOVE_TICKS = 5 // ein Schritt Laufen: 5 Spielticks, etwa ein Block
const DIG_TIMEOUT_MS = 10000
const PITCHES = [-Math.PI / 3, 0, Math.PI / 4] // nach unten, geradeaus, nach oben (Mineflayer: positiv = oben)
const FACINGS = [[0, -1], [-1, 0], [0, 1], [1, 0]] // Norden, Westen, Süden, Osten als (dx, dz)

// Die Rezepte, die eine Taste herstellen kann. Wie Crafters Tasten „make_wood_pickaxe“ usw.:
// Welche Taste was macht und was man dafür braucht, muss der Agent selbst herausfinden.
const RECIPES = [
  'planks', // aus jedem Stamm
  'stick',
  'crafting_table',
  'wooden_pickaxe',
  'wooden_sword',
  'stone_pickaxe',
  'stone_sword',
  'furnace',
  'torch'
]

const ACTIONS = [
  'nichts',
  'vor',
  'zurück',
  'links',
  'rechts',
  'springen',
  'links drehen',
  'rechts drehen',
  'hoch schauen',
  'runter schauen',
  'angreifen',
  'benutzen',
  'nächstes Fach',
  'voriges Fach',
  ...RECIPES.map(name => `herstellen ${name}`)
]

function layoutNames () {
  const names = []
  for (const dy of LAYERS) {
    for (let dz = 0; dz < VIEW; dz++) {
      for (let dx = 0; dx < VIEW; dx++) names.push(`Block ${offset(dx)},${dy},${offset(dz)}`)
    }
  }
  for (let dz = 0; dz < VIEW; dz++) {
    for (let dx = 0; dx < VIEW; dx++) names.push(`Wesen ${offset(dx)},${offset(dz)}`)
  }
  names.push('Block im Blick', 'Wesen im Blick')
  for (let slot = 0; slot < 9; slot++) names.push(`Fach ${slot + 1} Ding`, `Fach ${slot + 1} Anzahl`)
  names.push('gewähltes Fach', 'Leben', 'Hunger', 'Blick x', 'Blick z', 'Blick hoch')
  names.push('Ort x', 'Ort y', 'Ort z', 'Tageszeit')
  return names
}

function offset (index) {
  const value = index - Math.floor(VIEW / 2)
  return value >= 0 ? `+${value}` : `${value}`
}

const LAYOUT = layoutNames()

// Fortschritte (Advancements), wie der Server sie dem Spieler meldet, damit er sie im Menü
// sieht. Gezählt werden nur die, die das Spiel auch anzeigt: Rezepte und versteckte Einträge
// ohne Anzeige zählen nicht.
class Progress {
  constructor () {
    this.requirements = new Map() // Fortschritt -> Gruppen von Kriterien (eins je Gruppe nötig)
    this.obtained = new Map() // Fortschritt -> erfüllte Kriterien
    this.done = new Set()
    this.fresh = []
  }

  update (packet) {
    if (packet.reset) { this.requirements.clear(); this.obtained.clear() }
    for (const { key, value } of packet.advancementMapping) {
      if (value.displayData) this.requirements.set(key, value.requirements)
    }
    for (const key of packet.identifiers) this.requirements.delete(key)
    for (const { key, value } of packet.progressMapping) {
      const met = this.obtained.get(key) ?? new Set()
      for (const { criterionIdentifier, criterionProgress } of value) {
        if (criterionProgress === undefined) met.delete(criterionIdentifier)
        else met.add(criterionIdentifier)
      }
      this.obtained.set(key, met)
    }
    for (const [key, groups] of this.requirements) {
      const met = this.obtained.get(key) ?? new Set()
      const complete = groups.length > 0 && groups.every(group => group.some(name => met.has(name)))
      if (complete && !this.done.has(key)) { this.done.add(key); this.fresh.push(key) }
      if (!complete) this.done.delete(key)
    }
  }

  takeNew () {
    const fresh = this.fresh
    this.fresh = []
    return fresh
  }
}

class Player {
  constructor (bot) {
    this.bot = bot
    this.facing = 0
    this.pitch = 1
    this.progress = new Progress()
    this.dead = false
    bot._client.on('advancements', packet => this.progress.update(packet))
    // Tod erkennen: Mineflayers „death“ kommt nicht immer (sofortiges Wiedererscheinen),
    // deshalb zählt auch jedes neue Erscheinen nach dem Rundenbeginn und Leben 0.
    this.playing = false
    bot.on('death', () => { this.dead = true })
    bot.on('spawn', () => { if (this.playing) this.dead = true })
  }

  async reset (seed, record) {
    this.playing = false
    const name = this.bot.username
    for (const command of [
      `/clear ${name}`,
      `/effect clear ${name}`,
      `/advancement revoke ${name} everything`,
      `/xp set ${name} 0 levels`,
      '/time set day'
    ]) await this.command(command)
    await this.travel(mulberry32(seed))
    await this.command(`/effect give ${name} instant_health 1 10`)
    await this.command(`/effect give ${name} saturation 1 20`)
    this.facing = 0
    this.pitch = 1
    await this.look()
    this.progress.takeNew() // was vor dem Rundenbeginn kam, zählt nicht
    this.dead = false
    this.playing = true
    return this.answer(record ? 'Start' : null)
  }

  // Ein neuer Ort für die Runde: wie bei Crafter auf Land mit Bäumen in der Nähe, nicht auf
  // dem offenen oder gefrorenen Meer. Das ist die Wahl des Startplatzes, kein Wissen für den
  // Agenten. Nach einigen Versuchen gilt der letzte Ort.
  async travel (random) {
    for (let attempt = 0; attempt < START_ATTEMPTS; attempt++) {
      const x = Math.floor((random() - 0.5) * 20000)
      const z = Math.floor((random() - 0.5) * 20000)
      await this.command(`/spreadplayers ${x} ${z} 0 50 false ${this.bot.username}`)
      await this.ticks(40) // bis die Chunks am neuen Ort da sind
      await this.bot.waitForChunksToLoad()
      if (this.goodStart()) return
    }
  }

  goodStart () {
    const below = this.bot.blockAt(this.bot.entity.position.offset(0, -1, 0))
    if (!below || /water|ice/.test(below.name)) return false
    const registry = this.bot.registry
    const logs = registry.blocksArray.filter(block => block.name.endsWith('_log')).map(block => block.id)
    return this.bot.findBlock({ matching: logs, maxDistance: 24 }) !== null
  }

  async command (text) {
    this.bot.chat(text)
    await this.ticks(2)
  }

  async step (action, record) {
    const name = ACTIONS[action]
    if (name === undefined) throw new Error(`Taste ${action} gibt es nicht`)
    // Stirbt die Figur zwischen zwei Befehlen, endet die Runde mit dieser Antwort; Mineflayer
    // lässt sie von selbst wieder erscheinen, und `reset` beginnt die nächste Runde.
    if (!this.dead) await this.act(name)
    return this.answer(record ? name : null)
  }

  async act (name) {
    const moves = { vor: ['forward'], zurück: ['back'], links: ['left'], rechts: ['right'], springen: ['forward', 'jump'] }
    if (name in moves) return this.hold(moves[name])
    if (name === 'links drehen') { this.facing = (this.facing + 1) % 4; return this.look() }
    if (name === 'rechts drehen') { this.facing = (this.facing + 3) % 4; return this.look() }
    if (name === 'hoch schauen') { this.pitch = Math.min(this.pitch + 1, PITCHES.length - 1); return this.look() }
    if (name === 'runter schauen') { this.pitch = Math.max(this.pitch - 1, 0); return this.look() }
    if (name === 'angreifen') return this.attack()
    if (name === 'benutzen') return this.use()
    if (name === 'nächstes Fach') return this.bot.setQuickBarSlot((this.bot.quickBarSlot + 1) % 9)
    if (name === 'voriges Fach') return this.bot.setQuickBarSlot((this.bot.quickBarSlot + 8) % 9)
    if (name.startsWith('herstellen ')) return this.craft(name.slice('herstellen '.length))
    return this.ticks(MOVE_TICKS) // nichts
  }

  async hold (controls) {
    for (const control of controls) this.bot.setControlState(control, true)
    await this.ticks(MOVE_TICKS)
    this.bot.clearControlStates()
    await this.ticks(1)
  }

  async look () {
    const [dx, dz] = FACINGS[this.facing]
    // Mineflayer: Gierwinkel 0 schaut nach Norden (−z), positiver Winkel dreht nach Westen.
    const yaw = Math.atan2(-dx, -dz)
    await this.bot.look(yaw, PITCHES[this.pitch], true)
  }

  async attack () {
    const entity = this.entityInSight()
    if (entity) { this.bot.attack(entity); return this.ticks(MOVE_TICKS) }
    const block = this.bot.blockAtCursor(REACH)
    if (block && block.diggable && this.bot.canDigBlock(block)) {
      await withTimeout(this.bot.dig(block, true), DIG_TIMEOUT_MS).catch(() => this.bot.stopDigging())
      return this.ticks(MOVE_TICKS) // Zeit, damit die Beute aufgesammelt werden kann
    }
    this.bot.swingArm()
    return this.ticks(MOVE_TICKS)
  }

  async use () {
    const item = this.bot.heldItem
    const block = this.bot.blockAtCursor(REACH)
    const isBlock = item && this.bot.registry.blocksByName[item.name] !== undefined
    try {
      if (item && this.bot.registry.foodsByName[item.name] && this.bot.food < 20) {
        await withTimeout(this.bot.consume(), 4000)
      } else if (item && isBlock && block) {
        await withTimeout(this.bot.placeBlock(block, new Vec3(0, 1, 0)), 2000)
      } else if (block && !isBlock) {
        await withTimeout(this.bot.activateBlock(block), 2000)
      } else {
        this.bot.activateItem()
        await this.ticks(MOVE_TICKS)
        this.bot.deactivateItem()
      }
    } catch (error) {
      // Geht etwas nicht (kein Platz, nichts zu benutzen), passiert eben nichts.
    }
    return this.ticks(1)
  }

  async craft (name) {
    const registry = this.bot.registry
    const table = this.bot.findBlock({ matching: registry.blocksByName.crafting_table.id, maxDistance: REACH })
    const wanted = name === 'planks'
      ? registry.itemsArray.filter(item => item.name.endsWith('_planks'))
      : [registry.itemsByName[name]]
    for (const item of wanted) {
      const recipe = this.bot.recipesFor(item.id, null, 1, table)[0]
      if (!recipe) continue
      try { await withTimeout(this.bot.craft(recipe, 1, table ?? undefined), 3000) } catch (error) { }
      break
    }
    return this.ticks(1)
  }

  entityInSight () {
    const eye = this.bot.entity.position.offset(0, this.bot.entity.height * 0.9, 0)
    let best = null
    for (const entity of Object.values(this.bot.entities)) {
      if (entity === this.bot.entity || entity.name === 'item') continue
      const distance = entity.position.distanceTo(eye)
      if (distance > 3) continue
      const toward = entity.position.offset(0, (entity.height || 1) / 2, 0).minus(eye).normalize()
      const view = viewVector(this.bot.entity.yaw, this.bot.entity.pitch)
      if (toward.dot(view) > 0.9 && (!best || distance < best.distance)) best = { entity, distance }
    }
    return best ? best.entity : null
  }

  answer (recordAction) {
    if (this.playing && this.bot.health !== undefined && this.bot.health <= 0) this.dead = true
    const answer = { inner: this.observe(), advancements: this.progress.takeNew(), dead: this.dead }
    if (recordAction !== null) answer.scene = this.scene(recordAction)
    return answer
  }

  // Ein Bild der Lage für die Wiedergabe-Seite, mit Namen. Geht nur an die Seite, nie an den
  // Agenten: Der Python-Adapter reicht es an der Wiring vorbei durch.
  scene (action) {
    const bot = this.bot
    const feet = bot.entity.position.floored()
    const half = Math.floor(SCENE / 2)
    const columns = []
    for (let dz = -half; dz <= half; dz++) {
      const row = []
      for (let dx = -half; dx <= half; dx++) row.push(this.surface(feet.offset(dx, 0, dz)))
      columns.push(row)
    }
    const entities = []
    for (const entity of Object.values(bot.entities)) {
      if (entity === bot.entity) continue
      const at = entity.position.floored().minus(feet)
      if (Math.abs(at.x) <= half && Math.abs(at.z) <= half && Math.abs(at.y) <= 6) {
        entities.push([entity.name || 'unbekannt', at.x, at.z])
      }
    }
    const cursor = bot.blockAtCursor(REACH)
    return {
      action,
      position: [feet.x, feet.y, feet.z],
      facing: FACINGS[this.facing],
      pitch: this.pitch - 1,
      health: Math.round(bot.health ?? 20),
      food: Math.round(bot.food ?? 20),
      held: bot.quickBarSlot,
      hotbar: Array.from({ length: 9 }, (_, slot) => {
        const item = bot.inventory.slots[bot.inventory.hotbarStart + slot]
        return item ? [item.name, item.count] : null
      }),
      cursor: cursor ? cursor.name : null,
      time: (bot.time && bot.time.timeOfDay) || 0,
      columns,
      entities
    }
  }

  surface (column) {
    // Der oberste feste Block einer Spalte, von Kopfhöhe + 4 abwärts, mit Höhe zu den Füßen.
    for (let dy = 4; dy >= -8; dy--) {
      const block = this.bot.blockAt(column.offset(0, dy, 0))
      if (block && block.name !== 'air' && block.name !== 'cave_air') return [block.name, dy]
    }
    return ['?', -9]
  }

  observe () {
    const bot = this.bot
    const feet = bot.entity.position.floored()
    const half = Math.floor(VIEW / 2)
    const inner = []
    for (const dy of LAYERS) {
      for (let dz = -half; dz <= half; dz++) {
        for (let dx = -half; dx <= half; dx++) {
          const block = bot.blockAt(feet.offset(dx, dy, dz))
          inner.push(block ? block.type : -1)
        }
      }
    }
    const beings = new Map()
    for (const entity of Object.values(bot.entities)) {
      if (entity === bot.entity) continue
      const cell = entity.position.floored().minus(feet)
      if (Math.abs(cell.x) > half || Math.abs(cell.z) > half || cell.y < -1 || cell.y > 2) continue
      beings.set(`${cell.x},${cell.z}`, entity.entityType + 1)
    }
    for (let dz = -half; dz <= half; dz++) {
      for (let dx = -half; dx <= half; dx++) inner.push(beings.get(`${dx},${dz}`) ?? 0)
    }
    const block = bot.blockAtCursor(REACH)
    const entity = this.entityInSight()
    inner.push(block ? block.type : -1, entity ? entity.entityType + 1 : 0)
    for (let slot = 0; slot < 9; slot++) {
      const item = bot.inventory.slots[bot.inventory.hotbarStart + slot]
      inner.push(item ? item.type + 1 : 0, item ? item.count : 0)
    }
    const [dx, dz] = FACINGS[this.facing]
    inner.push(bot.quickBarSlot, Math.round(bot.health ?? 20), Math.round(bot.food ?? 20))
    inner.push(dx, dz, this.pitch - 1, feet.x, feet.y, feet.z)
    inner.push(Math.floor(((bot.time && bot.time.timeOfDay) || 0) / 1000))
    if (inner.length !== LAYOUT.length) throw new Error(`Beobachtung hat ${inner.length} statt ${LAYOUT.length} Zahlen`)
    return inner
  }

  ticks (count) {
    return this.bot.waitForTicks(count)
  }
}

function viewVector (yaw, pitch) {
  return new Vec3(-Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), -Math.cos(yaw) * Math.cos(pitch))
}

function withTimeout (promise, ms) {
  let timer
  const timeout = new Promise((resolve, reject) => { timer = setTimeout(() => reject(new Error('Zeit um')), ms) })
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer))
}

function mulberry32 (seed) {
  // Kleiner, fester Zufallsgenerator, damit derselbe Startwert denselben Ort ergibt.
  let state = seed >>> 0
  return () => {
    state = (state + 0x6D2B79F5) >>> 0
    let t = state
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function parseArgs (argv) {
  const options = { host: 'localhost', port: 25565, username: 'hekmat', version: '1.20.4' }
  for (let i = 0; i < argv.length; i += 2) options[argv[i].replace(/^--/, '')] = argv[i + 1]
  options.port = Number(options.port)
  return options
}

async function main () {
  const options = parseArgs(process.argv.slice(2))
  const bot = mineflayer.createBot({ ...options, auth: 'offline' })
  bot.on('error', error => process.stderr.write(`Mineflayer: ${error.message}\n`))
  bot.on('kicked', reason => { process.stderr.write(`Vom Server geworfen: ${reason}\n`); process.exit(2) })
  await new Promise(resolve => bot.once('spawn', resolve))
  await bot.waitForChunksToLoad()
  bot.chat('/gamerule announceAdvancements true')
  bot.chat('/gamerule doImmediateRespawn true')
  const player = new Player(bot)
  send({ ready: true, layout: LAYOUT, actions: ACTIONS })

  const lines = readline.createInterface({ input: process.stdin })
  for await (const line of lines) {
    const request = JSON.parse(line)
    let answer
    try {
      if (request.op === 'reset') answer = await player.reset(request.seed, request.record)
      else if (request.op === 'step') answer = await player.step(request.action, request.record)
      else if (request.op === 'close') break
      else answer = { error: `Unbekannter Befehl: ${request.op}` }
    } catch (error) {
      answer = { error: error.message }
    }
    send(answer)
  }
  bot.quit()
  process.exit(0)
}

main().catch(error => {
  process.stderr.write(`${error.stack}\n`)
  process.exit(1)
})
