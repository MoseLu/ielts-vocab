import { readdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'

const rootDir = process.cwd()
const styleRoot = path.join(rootDir, 'frontend', 'src', 'styles')
const sourceRoot = path.join(rootDir, 'frontend', 'src')
const styleTokenSources = new Set([
  path.join(styleRoot, 'base.scss'),
  path.join(styleRoot, 'base.tokens.scss'),
  path.join(styleRoot, 'base.mix-tokens.scss'),
])

function walk(dir, predicate) {
  const files = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      files.push(...walk(fullPath, predicate))
      continue
    }
    if (entry.isFile() && predicate(fullPath)) {
      files.push(fullPath)
    }
  }
  return files
}

function toRepoPath(absolutePath) {
  return path.relative(rootDir, absolutePath).replace(/\\/g, '/')
}

function stripBlockComments(content) {
  return content.replace(/\/\*[\s\S]*?\*\//g, (match) => match.replace(/[^\n]/g, ' '))
}

function buildLineStarts(content) {
  const starts = [0]
  for (let index = 0; index < content.length; index += 1) {
    if (content[index] === '\n') {
      starts.push(index + 1)
    }
  }
  return starts
}

function lineNumberAt(offset, lineStarts) {
  let low = 0
  let high = lineStarts.length - 1
  while (low <= high) {
    const mid = Math.floor((low + high) / 2)
    if (lineStarts[mid] <= offset) {
      low = mid + 1
    } else {
      high = mid - 1
    }
  }
  return high + 1
}

function report(errors, absolutePath, line, message) {
  errors.push(`${toRepoPath(absolutePath)}:${line}: ${message}`)
}

function findStyleBlocks(content) {
  const blocks = []
  let searchStart = 0
  while (true) {
    const start = content.indexOf('style={{', searchStart)
    if (start === -1) {
      return blocks
    }
    let cursor = start + 'style={{'.length
    let depth = 2
    while (cursor < content.length && depth > 0) {
      const char = content[cursor]
      if (char === '{') {
        depth += 1
      } else if (char === '}') {
        depth -= 1
      }
      cursor += 1
    }
    blocks.push({ start, end: cursor, raw: content.slice(start, cursor) })
    searchStart = cursor
  }
}

function findColorMixCalls(content) {
  const calls = []
  let searchStart = 0
  while (true) {
    const start = content.indexOf('color-mix(', searchStart)
    if (start === -1) {
      return calls
    }
    let cursor = start + 'color-mix('.length
    let depth = 1
    while (cursor < content.length && depth > 0) {
      const char = content[cursor]
      if (char === '(') {
        depth += 1
      } else if (char === ')') {
        depth -= 1
      }
      cursor += 1
    }
    calls.push({ start, end: cursor, raw: content.slice(start, cursor) })
    searchStart = cursor
  }
}

const styleFiles = walk(styleRoot, (fullPath) => fullPath.endsWith('.scss'))
const sourceFiles = walk(sourceRoot, (fullPath) => /\.(tsx|ts)$/.test(fullPath))
const errors = []

for (const absolutePath of styleFiles) {
  if (styleTokenSources.has(absolutePath)) {
    continue
  }

  const original = readFileSync(absolutePath, 'utf8')
  const content = stripBlockComments(original)
  const lineStarts = buildLineStarts(content)

  for (const match of content.matchAll(/transition:\s*all\b/g)) {
    report(errors, absolutePath, lineNumberAt(match.index ?? 0, lineStarts), '禁止 `transition: all`，请改用 motion token 组合')
  }

  for (const match of content.matchAll(/z-index:\s*-?\d+\b/g)) {
    report(errors, absolutePath, lineNumberAt(match.index ?? 0, lineStarts), '禁止硬编码 z-index，请改用 layer token')
  }

  for (const match of content.matchAll(/\dvar\(--size-/g)) {
    report(errors, absolutePath, lineNumberAt(match.index ?? 0, lineStarts), '检测到损坏的 size token 拼接，请修复为单个 `var(--size-*)`')
  }

  for (const match of content.matchAll(/rgba\(var\([^)]*\),\s*(?:0|1|0?\.\d+)\)/g)) {
    report(errors, absolutePath, lineNumberAt(match.index ?? 0, lineStarts), 'rgba alpha 必须改用 `var(--alpha-*)` token')
  }

  for (const call of findColorMixCalls(content)) {
    const percentMatch = call.raw.match(/\b\d+%/g)
    if (percentMatch) {
      report(errors, absolutePath, lineNumberAt(call.start, lineStarts), 'color-mix 百分比必须改用 `var(--mix-*)` token')
    }
  }

  const lines = content.split(/\r?\n/)
  lines.forEach((line, index) => {
    const trimmed = line.trim()
    if (trimmed.length === 0 || trimmed.startsWith('@media')) {
      return
    }
    const scrubbed = line
      .replace(/env\([^)]*,\s*0px\)/g, 'env-token')
      .replace(/var\([^)]*,\s*0px\)/g, 'var-token')
    const rawPxMatch = scrubbed.match(/\b(?!0px\b)\d+(?:\.\d+)?px\b/)
    if (rawPxMatch) {
      report(errors, absolutePath, index + 1, '固定像素尺寸必须改用 design token')
    }
  })
}

for (const absolutePath of sourceFiles) {
  const content = readFileSync(absolutePath, 'utf8')
  const lineStarts = buildLineStarts(content)

  for (const block of findStyleBlocks(content)) {
    const body = block.raw.replace(/^style=\{\{/, '').replace(/\}\}$/, '')
    const bareKeys = [...body.matchAll(/(?:^|[,{]\s*)([A-Za-z_$][\w$-]*)\s*:/g)]
      .map((match) => match[1])
      .filter((key) => !key.startsWith('--'))
    const quotedKeys = [...body.matchAll(/(?:^|[,{]\s*)['"]([^'"]+)['"]\s*:/g)]
      .map((match) => match[1])
      .filter((key) => !key.startsWith('--'))

    if (bareKeys.length > 0 || quotedKeys.length > 0) {
      report(errors, absolutePath, lineNumberAt(block.start, lineStarts), 'inline style 仅允许写 CSS custom property（`--*`）')
    }
  }
}

if (errors.length > 0) {
  console.error('Design token usage check failed:\n')
  for (const error of errors) {
    console.error(`- ${error}`)
  }
  process.exit(1)
}

console.log('Design token usage check passed.')
