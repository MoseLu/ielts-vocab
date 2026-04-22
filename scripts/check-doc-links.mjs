import fs from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..')

const fixMode = process.argv.includes('--fix')

const targetFiles = [
  'README.md',
  'backend/API.md',
  'backend/README.md',
  'docs/README.md',
]

const targetDirectories = [
  'docs/architecture',
  'docs/governance',
  'docs/milestones',
  'docs/operations',
  'docs/planning',
]

const forbiddenPatterns = [
  { pattern: /Bearer Token/i, label: 'legacy auth wording "Bearer Token"' },
  { pattern: /JWT \+ localStorage/i, label: 'legacy auth wording "JWT + localStorage"' },
]

const placeholderTargets = new Set([
  'ABSOLUTE_PATH_HERE',
  'RELATIVE_PATH_HERE',
])

const markdownLinkPattern = /\[[^\]]*]\(([^)]+)\)/g
const absoluteRepoPathPattern = /^\/?([A-Za-z]:\/enterprise-workspace\/projects\/ielts-vocab\/.+)$/i

function normalizeTarget(target) {
  if (target.startsWith('<') && target.endsWith('>')) {
    return target.slice(1, -1)
  }
  return target
}

function splitTarget(target) {
  const hashIndex = target.indexOf('#')
  const queryIndex = target.indexOf('?')
  const cutIndex = [hashIndex, queryIndex]
    .filter(index => index >= 0)
    .reduce((min, index) => Math.min(min, index), Number.POSITIVE_INFINITY)

  if (!Number.isFinite(cutIndex)) {
    return { pathname: target, suffix: '' }
  }

  return {
    pathname: target.slice(0, cutIndex),
    suffix: target.slice(cutIndex),
  }
}

function toPosixRelative(fromFile, repoRelativePath) {
  const fromDir = path.dirname(fromFile)
  let relativePath = path.relative(fromDir, path.join(repoRoot, repoRelativePath))
  if (!relativePath.startsWith('.')) {
    relativePath = `./${relativePath}`
  }
  return relativePath.replaceAll(path.sep, '/')
}

function isExternalLink(target) {
  return /^(?:[a-z]+:|\/\/)/i.test(target)
}

function isPlaceholderLink(target) {
  return placeholderTargets.has(target)
}

async function collectTargetFiles() {
  const collected = new Set(targetFiles.map(file => path.join(repoRoot, file)))

  for (const relativeDir of targetDirectories) {
    const absoluteDir = path.join(repoRoot, relativeDir)
    await walkDirectory(absoluteDir, collected)
  }

  return [...collected].sort()
}

async function walkDirectory(directory, collected) {
  const entries = await fs.readdir(directory, { withFileTypes: true })
  for (const entry of entries) {
    const absolutePath = path.join(directory, entry.name)
    if (entry.isDirectory()) {
      await walkDirectory(absolutePath, collected)
      continue
    }
    if (entry.isFile() && entry.name.endsWith('.md')) {
      collected.add(absolutePath)
    }
  }
}

async function pathExists(filePath) {
  try {
    await fs.access(filePath)
    return true
  } catch {
    return false
  }
}

async function main() {
  const files = await collectTargetFiles()
  const issues = []

  for (const absoluteFile of files) {
    const originalText = await fs.readFile(absoluteFile, 'utf8')
    let nextText = originalText

    nextText = nextText.replace(markdownLinkPattern, (fullMatch, rawTarget) => {
      const target = normalizeTarget(rawTarget.trim())
      const { pathname, suffix } = splitTarget(target)
      const absoluteMatch = pathname.match(absoluteRepoPathPattern)
      if (!absoluteMatch) return fullMatch

      const windowsPath = absoluteMatch[1].replaceAll('/', path.sep)
      const repoRelativePath = path.relative(repoRoot, windowsPath)
      const relativeTarget = `${toPosixRelative(absoluteFile, repoRelativePath)}${suffix}`
      return fullMatch.replace(rawTarget, relativeTarget)
    })

    if (fixMode && nextText !== originalText) {
      await fs.writeFile(absoluteFile, nextText, 'utf8')
    }

    const textToCheck = fixMode ? nextText : originalText
    const repoRelativeFile = path.relative(repoRoot, absoluteFile).replaceAll(path.sep, '/')

    for (const { pattern, label } of forbiddenPatterns) {
      if (pattern.test(textToCheck)) {
        issues.push(`${repoRelativeFile}: contains ${label}`)
      }
    }

    const matches = [...textToCheck.matchAll(markdownLinkPattern)]
    for (const match of matches) {
      const rawTarget = match[1]
      const target = normalizeTarget(rawTarget.trim())
      if (!target || target.startsWith('#') || isExternalLink(target)) {
        continue
      }

      const { pathname } = splitTarget(target)
      if (!pathname) {
        continue
      }

      if (isPlaceholderLink(pathname)) {
        continue
      }

      if (absoluteRepoPathPattern.test(pathname)) {
        issues.push(`${repoRelativeFile}: contains repo-absolute link target ${pathname}`)
        continue
      }

      const resolvedPath = path.resolve(path.dirname(absoluteFile), pathname)
      if (!(await pathExists(resolvedPath))) {
        issues.push(`${repoRelativeFile}: broken relative link ${pathname}`)
      }
    }
  }

  if (issues.length > 0) {
    console.error('Documentation guard failed:')
    for (const issue of issues) {
      console.error(`- ${issue}`)
    }
    process.exitCode = 1
    return
  }

  console.log(`Documentation guard passed for ${files.length} files.`)
}

await main()
