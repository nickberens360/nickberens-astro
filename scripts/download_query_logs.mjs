#!/usr/bin/env node
// Download the server's raw query logs to local query-logs/ directory.
// Uses /admin/query-logs/download (Bearer protected) on your backend.

import { readFileSync, mkdirSync, existsSync, copyFileSync, createWriteStream, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { pipeline } from 'node:stream/promises';

function loadDotEnvIfPresent() {
  try {
    const envPath = resolve(process.cwd(), '.env');
    if (!existsSync(envPath)) return;
    const content = readFileSync(envPath, 'utf8');
    for (const line of content.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eq = trimmed.indexOf('=');
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      let val = trimmed.slice(eq + 1).trim();
      // Remove surrounding quotes if present
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      if (!(key in process.env)) {
        process.env[key] = val;
      }
    }
  } catch {
    // ignore
  }
}

loadDotEnvIfPresent();

const API_URL = (process.env.LOGS_API_URL || process.env.PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const TOKEN = process.env.LOGS_BEARER_TOKEN || process.env.QUERY_LOG_AUTH_TOKEN;

if (!TOKEN) {
  console.error('Missing token. Set LOGS_BEARER_TOKEN or QUERY_LOG_AUTH_TOKEN in environment or .env');
  process.exit(1);
}

const outDir = resolve(process.cwd(), 'query-logs');
const ts = new Date().toISOString().replace(/[:.]/g, '-');
const outFile = resolve(outDir, `query_logs_${ts}.jsonl`);
const latestFile = resolve(outDir, 'latest.jsonl');

async function main() {
  mkdirSync(outDir, { recursive: true });

  const url = `${API_URL}/admin/query-logs/download`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${TOKEN}` },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    console.error(`Download failed: ${res.status} ${res.statusText} ${text ? '- ' + text : ''}`);
    process.exit(1);
  }

  // Use Readable.fromWeb to convert web stream to Node stream
  const { Readable } = await import('node:stream');
  await pipeline(Readable.fromWeb(res.body), createWriteStream(outFile));

  try {
    copyFileSync(outFile, latestFile);
  } catch (err) {
    console.warn(`Warning: Could not copy to 'latest.jsonl': ${err.message}`);
  }

  const bytes = statSync(outFile).size;
  console.log(`Saved ${bytes.toLocaleString()} bytes to ${outFile}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
