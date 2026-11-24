#!/usr/bin/env node
//
// make.fun bounty entry point — "Promote make.fun's make-your-own-bounty post on X".
// The deliverable of this bounty is the post that lives on X; this file is only the courier
// that hands that post's address to the grader. The house reads POST.json from the repository
// root and then reads the post it names, so the address has to be well formed before anything
// is copied: this program validates first and only then copies, which means a malformed or
// empty address can never slip through the gate and be scored as a silent zero.
// Node 22, ES modules, standard library only — no dependencies, no network, no child processes.
// The run is deterministic: identical input bytes always produce identical output bytes.
//
// Local run:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
//
import { mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

/** Where the grader mounts its output inside the container. */
const GRADER_MOUNT = "/output";
/** Name of the manifest the house reads, and of the file we hand back. */
const MANIFEST = "POST.json";
/** Refuse anything above this many bytes. */
const CEILING_BYTES = 16384;
/** The shape an X post address must have; the digits at the end are the post id. */
const STATUS_SHAPE =
  /^https?:\/\/(?:www\.|mobile\.)?(?:x\.com|twitter\.com)\/(?:[A-Za-z0-9_]{1,15}|i\/web)\/status\/(\d+)(?:[?#].*)?$/;

/**
 * Single exit hatch: one line to stderr, status 1, nothing else. Every refusal below funnels
 * through here so no stack trace can ever reach the operator or the gate.
 */
function reject(reason) {
  process.stderr.write(`error: ${reason}\n`);
  process.exit(1);
}

/** Output folder: the override when it is set and non-empty, otherwise the grader's mount. */
function outputFolder() {
  const override = process.env.MAKEFUN_OUTPUT_DIR;
  return override !== undefined && override !== "" ? override : GRADER_MOUNT;
}

/** Read the manifest as raw bytes. Never decode here — the copy has to stay byte-exact. */
function readManifest(absolutePath) {
  try {
    return readFileSync(absolutePath);
  } catch (err) {
    reject(`cannot read ${absolutePath}: ${err.message}`);
  }
}

/** Turn the bytes into a value, reporting the parser's own complaint when they are not JSON. */
function decodeManifest(bytes, absolutePath) {
  try {
    return JSON.parse(bytes.toString("utf8"));
  } catch (err) {
    reject(`${absolutePath} is not valid JSON: ${err.message}`);
  }
}

/** Pull the address out of the parsed manifest, insisting on a non-empty string. */
function extractAddress(value) {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    reject(`expected a JSON object with a single key, "url"`);
  }
  const raw = value.url;
  if (typeof raw !== "string") {
    reject(`the "url" property is missing or is not a string`);
  }
  const trimmed = raw.trim();
  if (trimmed === "") {
    reject(`the "url" property is empty`);
  }
  return trimmed;
}

/** Check the address against the X post shape and hand back the post id. */
function postIdOf(address) {
  const found = STATUS_SHAPE.exec(address);
  if (found === null) {
    reject(
      `"${address}" is not an X post address; expected https://x.com/<handle>/status/<id>`,
    );
  }
  return found[1];
}

/** Validate, then copy the raw bytes into the output folder and report on stdout. */
function deliver() {
  const sourcePath = resolve(process.cwd(), MANIFEST);

  const bytes = readManifest(sourcePath);

  if (bytes.length > CEILING_BYTES) {
    reject(`${sourcePath} is ${bytes.length} bytes, over the ${CEILING_BYTES}-byte cap`);
  }

  const address = extractAddress(decodeManifest(bytes, sourcePath));
  const postId = postIdOf(address);

  const folder = outputFolder();
  const destination = join(folder, MANIFEST);

  try {
    mkdirSync(folder, { recursive: true });
    writeFileSync(destination, bytes);
  } catch (err) {
    reject(`cannot write ${destination}: ${err.message}`);
  }

  const written = statSync(destination).size;
  process.stdout.write(`${destination} ${address} post ${postId} ${written} bytes\n`);
}

try {
  deliver();
} catch (err) {
  reject(err instanceof Error ? err.message : String(err));
}
