import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';

const configUrl = new URL('./file-line-limit.config.json', import.meta.url);
const config = JSON.parse(readFileSync(configUrl, 'utf8'));

function listGitFiles(args) {
  const output = execFileSync('git', args, {
    cwd: process.cwd(),
    encoding: 'buffer',
  });

  return output
    .toString('utf8')
    .split('\0')
    .filter(Boolean);
}

function getCandidateFiles() {
  const trackedFiles = listGitFiles(['ls-files', '-z']);
  const untrackedFiles = listGitFiles(['ls-files', '-z', '--others', '--exclude-standard']);
  return [...new Set([...trackedFiles, ...untrackedFiles])];
}

function isBinary(buffer) {
  const limit = Math.min(buffer.length, 8000);
  for (let i = 0; i < limit; i += 1) {
    if (buffer[i] === 0) {
      return true;
    }
  }

  return false;
}

function countLineBreaks(buffer, byte) {
  let count = 0;
  for (let i = 0; i < buffer.length; i += 1) {
    if (buffer[i] === byte) {
      count += 1;
    }
  }
  return count;
}

function countLines(buffer) {
  if (buffer.length === 0) {
    return 0;
  }

  const lfCount = countLineBreaks(buffer, 0x0a);
  if (lfCount > 0) {
    return buffer[buffer.length - 1] === 0x0a ? lfCount : lfCount + 1;
  }

  const crCount = countLineBreaks(buffer, 0x0d);
  if (crCount > 0) {
    return buffer[buffer.length - 1] === 0x0d ? crCount : crCount + 1;
  }

  return 1;
}

function matchesExemption(filePath, pattern) {
  if (pattern.endsWith('/**')) {
    const prefix = pattern.slice(0, -2);
    return filePath.startsWith(prefix);
  }

  return filePath === pattern;
}

function isExempt(filePath) {
  return config.exemptions.some((pattern) => matchesExemption(filePath, pattern));
}

const baseline = new Map(Object.entries(config.baseline));
const oversizeViolations = [];
const staleBaseline = [];

for (const filePath of getCandidateFiles()) {
  if (!existsSync(filePath)) {
    continue;
  }

  if (isExempt(filePath)) {
    continue;
  }

  const buffer = readFileSync(filePath);
  if (isBinary(buffer)) {
    continue;
  }

  const lines = countLines(buffer);
  const baselineLimit = baseline.get(filePath);

  if (lines > config.maxLines) {
    if (baselineLimit === undefined) {
      oversizeViolations.push(
        `${filePath}: ${lines} lines exceeds ${config.maxLines} and is not in the oversize baseline`,
      );
      continue;
    }

    if (lines > baselineLimit) {
      oversizeViolations.push(
        `${filePath}: ${lines} lines exceeds baseline allowance ${baselineLimit}`,
      );
    }

    baseline.delete(filePath);
    continue;
  }

  if (baselineLimit !== undefined) {
    staleBaseline.push(
      `${filePath}: ${lines} lines is now within limit ${config.maxLines}; remove it from the baseline`,
    );
    baseline.delete(filePath);
  }
}

for (const [filePath, baselineLimit] of baseline.entries()) {
  staleBaseline.push(
    `${filePath}: baseline entry ${baselineLimit} has no matching oversize file`,
  );
}

if (oversizeViolations.length > 0 || staleBaseline.length > 0) {
  console.error(`File line limit check failed (max ${config.maxLines} lines).`);

  if (oversizeViolations.length > 0) {
    console.error('\nOversize violations:');
    for (const violation of oversizeViolations) {
      console.error(`- ${violation}`);
    }
  }

  if (staleBaseline.length > 0) {
    console.error('\nBaseline cleanup required:');
    for (const entry of staleBaseline) {
      console.error(`- ${entry}`);
    }
  }

  process.exit(1);
}

console.log(
  `File line limit check passed. Baseline exceptions still tracked: ${Object.keys(config.baseline).length}.`,
);
