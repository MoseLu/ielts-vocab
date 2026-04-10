#!/usr/bin/env node

import { readFile, readdir, stat } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import process from 'node:process';
import { pathToFileURL } from 'node:url';

function printUsage() {
  console.error(
    'Usage: node backend/scripts/upload_word_tts_package_to_oss.mjs ' +
      '--payload <json> --env-file <backend/.env> --axi-root <axi-app-cli> [--concurrency <n>]',
  );
}

function parseArgs(argv) {
  const args = {
    concurrency: 8,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === '--help' || flag === '-h') {
      args.help = true;
      continue;
    }
    if (!flag.startsWith('--')) {
      throw new Error(`Unexpected argument: ${flag}`);
    }
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) {
      throw new Error(`Missing value after ${flag}`);
    }
    index += 1;
    if (flag === '--payload') {
      args.payload = value;
    } else if (flag === '--env-file') {
      args.envFile = value;
    } else if (flag === '--axi-root') {
      args.axiRoot = value;
    } else if (flag === '--concurrency') {
      args.concurrency = Number.parseInt(value, 10);
    } else {
      throw new Error(`Unknown flag: ${flag}`);
    }
  }

  return args;
}

function stripOptionalQuotes(rawValue) {
  const value = rawValue.trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }
  return value;
}

async function loadEnvFile(envFile) {
  const text = await readFile(envFile, 'utf8');
  for (const rawLine of text.split(/\r?\n/u)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) {
      continue;
    }
    const equalIndex = line.indexOf('=');
    if (equalIndex <= 0) {
      continue;
    }
    const key = line.slice(0, equalIndex).trim();
    const value = stripOptionalQuotes(line.slice(equalIndex + 1));
    if (!process.env[key]) {
      process.env[key] = value;
    }
  }
}

function readRequiredEnv(name) {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Missing required env: ${name}`);
  }
  return value;
}

async function findAliOssPackageJson(searchRoot, depth = 0) {
  if (depth > 6) {
    return null;
  }
  const directCandidate = path.join(searchRoot, 'node_modules', 'ali-oss', 'package.json');
  try {
    await stat(directCandidate);
    return directCandidate;
  } catch {}

  let entries = [];
  try {
    entries = await readdir(searchRoot, { withFileTypes: true });
  } catch {
    return null;
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }
    if (entry.name === '.git' || entry.name === 'dist' || entry.name === 'build') {
      continue;
    }
    const nested = await findAliOssPackageJson(path.join(searchRoot, entry.name), depth + 1);
    if (nested) {
      return nested;
    }
  }
  return null;
}

async function resolveOssConstructor(axiRoot) {
  const packageJsonPath = path.join(axiRoot, 'package.json');
  try {
    const requireFromAxi = createRequire(pathToFileURL(packageJsonPath).href);
    return requireFromAxi('ali-oss');
  } catch {}

  const fallbackPackageJson = await findAliOssPackageJson(path.join(axiRoot, 'tmp'));
  if (!fallbackPackageJson) {
    throw new Error(`Cannot find ali-oss under ${axiRoot}`);
  }
  console.error(`[OSS] fallback ali-oss from ${fallbackPackageJson}`);
  const requireFromFallback = createRequire(pathToFileURL(fallbackPackageJson).href);
  return requireFromFallback('ali-oss');
}

async function runPool(items, concurrency, worker) {
  let nextIndex = 0;
  const size = Math.max(1, Math.min(concurrency, items.length || 1));

  async function consume() {
    while (true) {
      const current = nextIndex;
      nextIndex += 1;
      if (current >= items.length) {
        return;
      }
      await worker(items[current], current);
    }
  }

  await Promise.all(Array.from({ length: size }, () => consume()));
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(String(error.message || error));
    printUsage();
    process.exitCode = 1;
    return;
  }

  if (args.help) {
    printUsage();
    return;
  }
  if (!args.payload || !args.envFile || !args.axiRoot) {
    printUsage();
    process.exitCode = 1;
    return;
  }

  await loadEnvFile(args.envFile);
  const payload = JSON.parse(await readFile(args.payload, 'utf8'));
  const entries = Array.isArray(payload.entries) ? payload.entries : [];
  if (entries.length === 0) {
    throw new Error('Upload payload has no entries.');
  }

  const OSS = await resolveOssConstructor(args.axiRoot);
  const accessKeyId = readRequiredEnv('AXI_ALIYUN_OSS_ACCESS_KEY_ID');
  const accessKeySecret = readRequiredEnv('AXI_ALIYUN_OSS_ACCESS_KEY_SECRET');
  const bucket = readRequiredEnv('AXI_ALIYUN_OSS_PRIVATE_BUCKET');
  const region = readRequiredEnv('AXI_ALIYUN_OSS_REGION');
  const endpoint = process.env.AXI_ALIYUN_OSS_ENDPOINT?.trim() || undefined;
  const stsToken = process.env.AXI_ALIYUN_OSS_STS_TOKEN?.trim() || undefined;

  const client = new OSS({
    accessKeyId,
    accessKeySecret,
    authorizationV4: true,
    bucket,
    region,
    secure: true,
    timeout: 60_000,
    ...(endpoint ? { endpoint } : {}),
    ...(stsToken ? { stsToken } : {}),
  });

  let completed = 0;
  const uploaded = [];
  await runPool(entries, Number.isFinite(args.concurrency) ? args.concurrency : 8, async (entry) => {
    if (!entry.file_path || !entry.object_key) {
      throw new Error(`Invalid upload entry: ${JSON.stringify(entry)}`);
    }
    const fileInfo = await stat(entry.file_path);
    if (!fileInfo.isFile()) {
      throw new Error(`Upload source is not a file: ${entry.file_path}`);
    }
    await client.put(entry.object_key, entry.file_path, {
      headers: {
        'Content-Type': 'audio/mpeg',
      },
    });
    completed += 1;
    if (completed % 100 === 0 || completed === entries.length) {
      console.error(`[OSS] uploaded ${completed}/${entries.length}`);
    }
    uploaded.push({
      fileName: entry.file_name,
      objectKey: entry.object_key,
      size: fileInfo.size,
      word: entry.word,
    });
  });

  if (payload.manifest_object_key) {
    const manifestBody = JSON.stringify(
      {
        cacheIdentity: payload.cache_identity ?? null,
        packageCount: payload.package_count ?? uploaded.length,
        packageEnd: payload.package_end ?? null,
        packageIndex: payload.package_index ?? null,
        packageStart: payload.package_start ?? null,
        uploadedAt: new Date().toISOString(),
        uploaded,
      },
      null,
      2,
    );
    await client.put(payload.manifest_object_key, Buffer.from(manifestBody, 'utf8'), {
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
      },
    });
  }

  process.stdout.write(
    JSON.stringify({
      bucket,
      cacheIdentity: payload.cache_identity ?? null,
      entryCount: entries.length,
      manifestObjectKey: payload.manifest_object_key ?? null,
      packageIndex: payload.package_index ?? null,
      uploadedCount: uploaded.length,
    }),
  );
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
