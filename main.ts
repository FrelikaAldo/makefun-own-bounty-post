#!/usr/bin/env node
// The entry program for make.fun's "Promote make.fun's make-your-own-bounty post on X" bounty.
//
// The work is the post on X, not this file: the house reads POST.json from the repository, reads
// the post it names through X's public read, and writes its own counts of the post to
// /output/post.counts.json after this program's runs. So this program has one job — copy POST.json
// into the output directory — and it validates the file first so a malformed address never reaches
// the gate as a silent zero.
//
// Node 22, standard library only, no dependencies, no network. Deterministic: two runs write the
// same bytes.
//
// Outside the grader's container, MAKEFUN_OUTPUT_DIR stands in for /output:
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const repoDir = fileURLToPath(new URL('.', import.meta.url));
const source = path.join(repoDir, 'POST.json');
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const dest = path.join(outDir, 'POST.json');

/** Stop with a message on stderr and exit 1: the gate would refuse this file anyway. */
function fail(message) {
  process.stderr.write(message + '\n');
  process.exit(1);
}

let raw;
try {
  raw = await readFile(source);
} catch (err) {
  fail(`error: ${source} is missing or unreadable: ${err.message}`);
}

// The gate caps POST.json at 16384 bytes; check it here rather than at the gate.
if (raw.byteLength > 16384) {
  fail(`error: ${source} is ${raw.byteLength} bytes, over the 16384-byte cap`);
}

let post;
try {
  post = JSON.parse(raw.toString('utf8'));
} catch (err) {
  fail(`error: ${source} is not valid JSON: ${err.message}`);
}

if (typeof post !== 'object' || post === null || Array.isArray(post)) {
  fail(`error: ${source} must hold a JSON object with one key, "url"`);
}

const url = post.url;
if (typeof url !== 'string' || url.trim() === '') {
  fail(`error: ${source} has no "url" string`);
}

// https://x.com/<handle>/status/<id>, the same on twitter.com, with or without a www./mobile.
// prefix or the /i/web/ form; a query or fragment after it is read past.
const shape =
  /^https?:\/\/(?:www\.|mobile\.)?(?:x|twitter)\.com\/(?:[A-Za-z0-9_]{1,15}|i\/web)\/status\/(\d+)(?:[?#].*)?$/;
const match = shape.exec(url.trim());
if (!match) {
  fail(
    `error: ${source} names ${JSON.stringify(url)}, which is not an X post's address; ` +
      `expected https://x.com/<handle>/status/<id>`,
  );
}

try {
  await mkdir(outDir, { recursive: true });
} catch (err) {
  fail(`error: cannot create the output directory ${outDir}: ${err.message}`);
}

try {
  await writeFile(dest, raw);
} catch (err) {
  fail(`error: cannot write ${dest}: ${err.message}`);
}

console.log(`${dest} ${url} post ${match[1]} ${raw.byteLength} bytes`);
