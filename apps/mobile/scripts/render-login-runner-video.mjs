import { mkdir, rm } from 'node:fs/promises'
import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const mobileRoot = path.resolve(__dirname, '..')
const repoRoot = path.resolve(mobileRoot, '../..')
const compositionDir = path.join(mobileRoot, 'hyperframes/login-runner')
const outputPath = path.join(mobileRoot, 'src/assets/login-runner.mp4')
const framesDir = path.join(compositionDir, '.frames')
const duration = 4
const fps = 30
const width = 720
const height = 920

const requireFromFrontend = createRequire(path.join(repoRoot, 'frontend/package.json'))
const { chromium } = requireFromFrontend('@playwright/test')

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: 'inherit' })
    child.on('error', reject)
    child.on('close', code => {
      if (code === 0) resolve()
      else reject(new Error(`${command} exited with ${code}`))
    })
  })
}

await rm(framesDir, { force: true, recursive: true })
await mkdir(framesDir, { recursive: true })

const browser = await chromium.launch({
  channel: 'chrome',
  headless: true,
})
const page = await browser.newPage({ viewport: { height, width } })
await page.goto(pathToFileURL(path.join(compositionDir, 'index.html')).href)
await page.waitForFunction(() => Boolean(window.__timelines && window.__timelines['login-runner']))

const totalFrames = duration * fps
for (let frame = 0; frame < totalFrames; frame += 1) {
  const second = frame / fps
  await page.evaluate(time => {
    const timeline = window.__timelines['login-runner']
    timeline.pause()
    timeline.seek(time, false)
  }, second)
  await page.screenshot({
    animations: 'disabled',
    path: path.join(framesDir, `frame-${String(frame).padStart(4, '0')}.png`),
  })
}

await browser.close()

await run('ffmpeg', [
  '-y',
  '-framerate',
  String(fps),
  '-i',
  path.join(framesDir, 'frame-%04d.png'),
  '-vf',
  'format=yuv420p',
  '-movflags',
  '+faststart',
  outputPath,
])

await rm(framesDir, { force: true, recursive: true })
console.log(`Rendered ${outputPath}`)
