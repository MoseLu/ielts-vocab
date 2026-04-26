import { execFileSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'

const assetRoot = join(process.cwd(), 'frontend/assets/game/campaign-v2')
const source = 'generated-static-svg'

const themes = [
  ['study-campus', 'Campus Study', ['#1f5f85', '#7dc8a5', '#ffd166']],
  ['work-business', 'Work Market', ['#334155', '#2dd4bf', '#f59e0b']],
  ['travel-transport', 'Travel Route', ['#155e75', '#38bdf8', '#f97316']],
  ['city-services', 'City Services', ['#374151', '#a7f3d0', '#facc15']],
  ['health-lifestyle', 'Health Life', ['#166534', '#86efac', '#fb7185']],
  ['environment-nature', 'Nature Path', ['#14532d', '#84cc16', '#60a5fa']],
  ['science-tech', 'Science Lab', ['#312e81', '#22d3ee', '#c084fc']],
  ['society-culture', 'Culture Media', ['#7c2d12', '#fbbf24', '#38bdf8']],
]

const modes = [
  ['spelling', 'SPELL', ['#1d4ed8', '#facc15']],
  ['pronunciation', 'VOICE', ['#0f766e', '#67e8f9']],
  ['definition', 'MEANING', ['#7c3aed', '#f0abfc']],
  ['speaking', 'SPEAK', ['#be123c', '#fdba74']],
  ['example', 'EXAMPLE', ['#166534', '#bef264']],
]

const sharedStates = [
  ['energy-empty', 'Energy Empty'],
  ['network-error', 'Network Error'],
  ['scene-generating', 'Generating Scene'],
  ['scene-failed', 'Scene Failed'],
  ['recovery-empty', 'Recovery Empty'],
  ['locked', 'Locked'],
]

const manifest = {
  version: 'campaign-v2-static-v1',
  sourceBooks: ['ielts_reading_premium', 'ielts_listening_premium'],
  assets: [],
}

function esc(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&apos;',
  })[char])
}

function writePng(relativePath, width, height, svg, meta) {
  const outPath = join(assetRoot, relativePath)
  mkdirSync(dirname(outPath), { recursive: true })
  const workDir = mkdtempSync(join(tmpdir(), 'campaign-v2-'))
  const svgPath = join(workDir, 'asset.svg')
  writeFileSync(svgPath, svg)
  execFileSync('sips', ['-s', 'format', 'png', svgPath, '--out', outPath], { stdio: 'ignore' })
  rmSync(workDir, { recursive: true, force: true })
  manifest.assets.push({ path: relativePath, width, height, source, ...meta })
}

function sceneSvg(width, height, title, colors, compact = false) {
  const [dark, mid, accent] = colors
  const nodeSize = compact ? 74 : 92
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${dark}"/><stop offset="0.55" stop-color="${mid}"/><stop offset="1" stop-color="#101827"/></linearGradient>
<filter id="shadow"><feDropShadow dx="0" dy="16" stdDeviation="18" flood-color="#06111f" flood-opacity="0.45"/></filter>
</defs>
<rect width="${width}" height="${height}" fill="url(#bg)"/>
<path d="M0 ${height * 0.74} C ${width * 0.18} ${height * 0.58}, ${width * 0.32} ${height * 0.92}, ${width * 0.52} ${height * 0.69} S ${width * 0.82} ${height * 0.42}, ${width} ${height * 0.55} L ${width} ${height} L0 ${height}Z" fill="#0f172a" opacity="0.42"/>
<path d="M${width * 0.08} ${height * 0.78} C ${width * 0.22} ${height * 0.68}, ${width * 0.34} ${height * 0.72}, ${width * 0.46} ${height * 0.60} S ${width * 0.68} ${height * 0.45}, ${width * 0.88} ${height * 0.35}" fill="none" stroke="#ffffff" stroke-opacity="0.30" stroke-width="${compact ? 10 : 16}" stroke-linecap="round"/>
${[0.1, 0.26, 0.43, 0.61, 0.78, 0.9].map((x, index) => `<circle cx="${width * x}" cy="${height * (0.76 - index * 0.075)}" r="${nodeSize}" fill="${accent}" opacity="${index % 2 ? 0.88 : 0.72}" filter="url(#shadow)"/><circle cx="${width * x}" cy="${height * (0.76 - index * 0.075)}" r="${nodeSize * 0.48}" fill="#fff7ed" opacity="0.85"/>`).join('')}
<g filter="url(#shadow)"><rect x="${width * 0.08}" y="${height * 0.08}" width="${width * 0.42}" height="${compact ? 132 : 150}" rx="28" fill="#09111f" opacity="0.58"/><text x="${width * 0.105}" y="${height * 0.08 + (compact ? 78 : 90)}" fill="#ffffff" font-family="Arial, sans-serif" font-size="${compact ? 62 : 76}" font-weight="800">${esc(title)}</text></g>
<rect x="${width * 0.66}" y="${height * 0.12}" width="${width * 0.18}" height="${height * 0.16}" rx="24" fill="#ffffff" opacity="0.18"/>
<rect x="${width * 0.72}" y="${height * 0.20}" width="${width * 0.20}" height="${height * 0.18}" rx="28" fill="#020617" opacity="0.18"/>
</svg>`
}

function cardSvg(width, height, title, colors) {
  const [dark, mid, accent] = colors
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="${dark}"/><stop offset="0.62" stop-color="${mid}"/><stop offset="1" stop-color="${accent}"/></linearGradient></defs>
<rect width="${width}" height="${height}" rx="36" fill="url(#bg)"/>
<circle cx="${width * 0.78}" cy="${height * 0.24}" r="${height * 0.22}" fill="#ffffff" opacity="0.18"/>
<path d="M0 ${height * 0.72} C ${width * 0.25} ${height * 0.55}, ${width * 0.48} ${height * 0.86}, ${width} ${height * 0.58} L ${width} ${height} L0 ${height}Z" fill="#020617" opacity="0.32"/>
<text x="${width * 0.08}" y="${height * 0.72}" fill="#ffffff" font-family="Arial, sans-serif" font-size="58" font-weight="800">${esc(title)}</text>
</svg>`
}

function iconSvg(size, label, colors, tone = 'normal') {
  const [dark, accent] = colors
  const fill = tone === 'failure' ? '#f87171' : tone === 'success' ? '#86efac' : accent
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
<rect width="${size}" height="${size}" rx="${Math.round(size * 0.18)}" fill="${dark}"/>
<circle cx="${size * 0.5}" cy="${size * 0.44}" r="${size * 0.28}" fill="${fill}" opacity="0.9"/>
<text x="50%" y="${size * 0.58}" text-anchor="middle" fill="#07111f" font-family="Arial, sans-serif" font-size="${Math.round(size * 0.18)}" font-weight="900">${esc(label.slice(0, 4))}</text>
</svg>`
}

for (const [themeId, title, colors] of themes) {
  writePng(`themes/${themeId}/desktop/map.png`, 1920, 1080, sceneSvg(1920, 1080, title, colors), { category: 'theme', themeId, device: 'desktop', variant: 'desktop-map', usage: 'main-map' })
  writePng(`themes/${themeId}/mobile/map.png`, 1080, 1920, sceneSvg(1080, 1920, title, colors, true), { category: 'theme', themeId, device: 'mobile', variant: 'mobile-map', usage: 'main-map' })
  writePng(`themes/${themeId}/desktop/select-card.png`, 960, 540, cardSvg(960, 540, title, colors), { category: 'theme', themeId, device: 'desktop', variant: 'select-card', usage: 'theme-card' })
  writePng(`themes/${themeId}/desktop/empty-state.png`, 640, 480, cardSvg(640, 480, 'No Route', colors), { category: 'theme', themeId, device: 'desktop', variant: 'empty-state', usage: 'empty-state' })
  writePng(`themes/${themeId}/desktop/boss-gate.png`, 512, 512, iconSvg(512, 'BOSS', [colors[0], colors[2]]), { category: 'theme', themeId, device: 'desktop', variant: 'boss-gate', usage: 'boss-entry' })
  writePng(`themes/${themeId}/desktop/reward-node.png`, 512, 512, iconSvg(512, 'GIFT', [colors[0], colors[2]], 'success'), { category: 'theme', themeId, device: 'desktop', variant: 'reward-node', usage: 'reward-entry' })
  for (const variant of ['chapter-node', 'chapter-node-locked', 'chapter-node-current', 'chapter-node-completed']) {
    const tone = variant.endsWith('locked') ? 'failure' : variant.endsWith('completed') ? 'success' : 'normal'
    writePng(`themes/${themeId}/desktop/${variant}.png`, 256, 256, iconSvg(256, 'NODE', [colors[0], colors[2]], tone), { category: 'theme', themeId, device: 'desktop', variant, usage: 'chapter-node' })
  }
}

for (const [modeId, label, colors] of modes) {
  writePng(`modes/${modeId}/stage-desktop.png`, 1600, 900, sceneSvg(1600, 900, label, [colors[0], '#334155', colors[1]]), { category: 'mode', modeId, device: 'desktop', variant: 'stage-desktop', usage: 'mode-stage' })
  writePng(`modes/${modeId}/stage-mobile.png`, 1080, 1920, sceneSvg(1080, 1920, label, [colors[0], '#334155', colors[1]], true), { category: 'mode', modeId, device: 'mobile', variant: 'stage-mobile', usage: 'mode-stage' })
  writePng(`modes/${modeId}/mode-icon.png`, 256, 256, iconSvg(256, label, colors), { category: 'mode', modeId, variant: 'mode-icon', usage: 'mode-icon' })
  writePng(`modes/${modeId}/feedback-success.png`, 512, 512, iconSvg(512, 'PASS', colors, 'success'), { category: 'mode', modeId, variant: 'feedback-success', usage: 'feedback' })
  writePng(`modes/${modeId}/feedback-failure.png`, 512, 512, iconSvg(512, 'MISS', colors, 'failure'), { category: 'mode', modeId, variant: 'feedback-failure', usage: 'feedback' })
}

for (const [variant, label] of sharedStates) {
  writePng(`shared/states/${variant}.png`, 512, 384, cardSvg(512, 384, label, ['#0f172a', '#475569', '#fbbf24']), { category: 'shared', variant, usage: 'system-state' })
}

for (const variant of ['default', 'hover', 'pressed', 'disabled']) {
  writePng(`shared/buttons/${variant}.png`, 360, 128, cardSvg(360, 128, variant.toUpperCase(), ['#1d4ed8', '#0f766e', '#facc15']), { category: 'shared', variant: `button-${variant}`, usage: 'button-state' })
}

writeFileSync(join(assetRoot, 'manifest.json'), `${JSON.stringify(manifest)}\n`)
console.log(`generated ${manifest.assets.length} campaign-v2 assets`)
