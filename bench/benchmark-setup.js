#!/usr/bin/env node
/**
 * benchmark-setup.js — install patches for benchmark
 *
 * Use: node bench/benchmark-setup.js
 * Does: npm init + install patchright + playwright
 *   + install chromium for both
 *
 * Skips if already installed (idempotent).
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const BENCH_DIR = path.join(__dirname, '..', 'bench-node');
fs.mkdirSync(BENCH_DIR, { recursive: true });

function cmd(s, opts = {}) {
  console.log(`> ${s}`);
  return execSync(s, { stdio: 'inherit', cwd: BENCH_DIR, ...opts });
}

function has(name) {
  try {
    require.resolve(name, { paths: [BENCH_DIR] });
    return true;
  } catch (_) {
    return false;
  }
}

if (!fs.existsSync(path.join(BENCH_DIR, 'package.json'))) {
  cmd('npm init -y > /dev/null');
}

if (!has('patchright')) {
  try { cmd('npm install patchright --no-audit --no-fund'); }
  catch (e) { console.log('⚠️  patchright install failed (likely missing system deps)'); }
} else {
  console.log('✅ patchright already installed');
}

if (!has('playwright')) {
  try { cmd('npm install playwright --no-audit --no-fund'); }
  catch (e) { console.log('⚠️  playwright install failed'); }
} else {
  console.log('✅ playwright already installed');
}

console.log('\n📦 Done. Run:');
console.log('   cd', BENCH_DIR);
console.log('   node ../patchright-vs-playwright.js');
