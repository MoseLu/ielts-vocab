import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const frontendRoot = process.cwd()
const layoutPath = resolve(frontendRoot, 'src/components/practice/page/game-mode/gameTemplateLayouts.json')
const layouts = JSON.parse(readFileSync(layoutPath, 'utf-8'))

const requiredSlots = {
  learningCenter: ['learningCenter.hero', 'learningCenter.todayPlan', 'learningCenter.actions'],
  wordChainMap: ['map.hud.level', 'map.hud.energy', 'map.hud.coins', 'map.hud.diamonds', 'map.title', 'map.word.1', 'map.word.5', 'map.side.word', 'map.action', 'map.bottom.word', 'map.bottom.progress'],
  mobileWordChainMap: ['map.hud.level', 'map.hud.energy', 'map.hud.coins', 'map.hud.diamonds', 'map.title', 'map.word.1', 'map.word.5', 'map.side.word', 'map.action', 'map.bottom.word', 'map.bottom.progress'],
  wordMission: ['mission.hud', 'mission.objective', 'mission.answerPanel'],
  refillState: ['refill.hud', 'refill.list', 'refill.objective', 'refill.answerPanel', 'refill.action'],
  stageSettlement: ['settlement.medal', 'settlement.copy', 'settlement.rewards', 'settlement.actions'],
  mobileWordMission: ['mobileMission.hud', 'mobileMission.objective', 'mobileMission.answerPanel'],
}

function pngSize(path) {
  const buffer = readFileSync(path)
  if (buffer.toString('ascii', 1, 4) !== 'PNG') throw new Error(`${path} is not a PNG`)
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) }
}

function assetPath(publicPath) {
  if (!publicPath.startsWith('/ui/')) throw new Error(`Unsupported template asset path ${publicPath}`)
  return resolve(frontendRoot, 'assets', publicPath.slice(1))
}

function intersects(a, b) {
  return a.x < b.x + b.width && a.x + a.width > b.x && a.y < b.y + b.height && a.y + a.height > b.y
}

const issues = []

for (const [layoutId, layout] of Object.entries(layouts)) {
  const path = assetPath(layout.image)
  const size = pngSize(path)
  if (size.width !== layout.naturalSize.width || size.height !== layout.naturalSize.height) {
    issues.push(`${layoutId}: expected ${layout.naturalSize.width}x${layout.naturalSize.height}, got ${size.width}x${size.height}`)
  }
  for (const requiredSlot of requiredSlots[layoutId] ?? []) {
    if (!layout.slots.some(slot => slot.id === requiredSlot)) issues.push(`${layoutId}: missing ${requiredSlot}`)
  }
  for (const slot of layout.slots) {
    if (slot.x < 0 || slot.y < 0 || slot.width <= 0 || slot.height <= 0) issues.push(`${layoutId}:${slot.id}: invalid rect`)
    if (slot.x + slot.width > size.width || slot.y + slot.height > size.height) {
      issues.push(`${layoutId}:${slot.id}: rect exceeds ${size.width}x${size.height}`)
    }
  }
  const strictSlots = layout.slots.filter(slot => !slot.allowOverlap)
  for (let index = 0; index < strictSlots.length; index += 1) {
    for (let next = index + 1; next < strictSlots.length; next += 1) {
      if (intersects(strictSlots[index], strictSlots[next])) {
        issues.push(`${layoutId}: overlapping slots ${strictSlots[index].id} and ${strictSlots[next].id}`)
      }
    }
  }
}

if (issues.length > 0) {
  console.error(issues.join('\n'))
  process.exit(1)
}

console.log(`Validated ${Object.keys(layouts).length} game template layouts`)
