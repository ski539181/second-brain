#!/usr/bin/env node
/**
 * patchright-vs-playwright.js
 *
 * Benchmark: patchright vs playwright on Cloudflare-protected targets.
 * Goal: hard numbers to decide which to use for FT data product.
 *
 * Usage:
 *   node bench/patchright-vs-playwright.js
 *   node bench/patchright-vs-playwright.js --targets custom.url,other.url
 *   node bench/patchright-vs-playwright.js --runs 3
 *
 * Output:
 *   - Console: live progress + summary
 *   - bench/results-<timestamp>.csv: raw data
 *   - bench/results-<timestamp>.md: human report
 *
 * Requires (peer, not bundled):
 *   npm i patchright playwright
 *   npx patchright install chromium
 *   npx playwright install chromium
 *
 * Note: Termux ARM64 may lack libgtk-3. Run on Mac/Linux x64 for real numbers.
 */

const fs = require('fs');
const path = require('path');

// ===== Config =====
const DEFAULT_TARGETS = [
  'https://nowsecure.nl',         // CF challenge page
  'https://bot.sannysoft.com',    // bot detection test
  'https://httpbin.org/headers',  // shows User-Agent
];

const args = process.argv.slice(2);
function getArg(name, defaultVal) {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : defaultVal;
}

const RUNS = parseInt(getArg('runs', '1'), 10);
const TARGETS = getArg('targets', DEFAULT_TARGETS.join(',')).split(',').map(s => s.trim());

const RESULTS_DIR = path.join(__dirname, 'results');
fs.mkdirSync(RESULTS_DIR, { recursive: true });

const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const CSV_PATH = path.join(RESULTS_DIR, `results-${TIMESTAMP}.csv`);
const MD_PATH = path.join(RESULTS_DIR, `results-${TIMESTAMP}.md`);

// ===== Lib detection =====
async function detectLib(name) {
  try {
    const mod = require(name);
    return { ok: true, mod, version: require(`${name}/package.json`).version };
  } catch (e) {
    return { ok: false, error: e.code === 'MODULE_NOT_FOUND' ? 'not installed' : e.message };
  }
}

// ===== Single test =====
async function timeRun(lib, target, runIdx) {
  const start = Date.now();
  const result = {
    lib,
    target,
    run: runIdx,
    success: false,
    status: 0,
    size: 0,
    time_ms: 0,
    error: null,
    ua: null,
  };
  let browser = null;
  try {
    browser = await lib.mod.chromium.launch({ headless: true });
    const ctx = await browser.newContext({
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    });
    const page = await ctx.newPage();
    const resp = await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
    result.status = resp ? resp.status() : 0;
    const body = await page.content();
    result.size = body.length;
    result.success = resp && resp.status() < 400 && body.length > 100;
    result.ua = await page.evaluate(() => navigator.userAgent);
    await ctx.close();
  } catch (e) {
    result.error = e.message.slice(0, 200);
  } finally {
    if (browser) {
      try { await browser.close(); } catch (_) {}
    }
    result.time_ms = Date.now() - start;
  }
  return result;
}

// ===== Main =====
(async () => {
  console.log('🧪 patchright vs playwright benchmark');
  console.log(`   Runs/target/lib: ${RUNS}`);
  console.log(`   Targets: ${TARGETS.length}\n`);

  const libs = ['patchright', 'playwright'];
  const detected = {};
  for (const name of libs) {
    detected[name] = await detectLib(name);
    if (detected[name].ok) {
      console.log(`✅ ${name} v${detected[name].version}`);
    } else {
      console.log(`❌ ${name}: ${detected[name].error}`);
    }
  }
  console.log('');

  const allResults = [];
  for (const name of libs) {
    if (!detected[name].ok) {
      console.log(`⏭️  Skipping ${name} (not installed)`);
      for (const t of TARGETS) {
        for (let i = 1; i <= RUNS; i++) {
          allResults.push({
            lib: name, target: t, run: i, success: false,
            status: 0, size: 0, time_ms: 0,
            error: detected[name].error, ua: null,
          });
        }
      }
      continue;
    }
    for (const target of TARGETS) {
      for (let i = 1; i <= RUNS; i++) {
        process.stdout.write(`  ${name.padEnd(11)} → ${target} (run ${i}/${RUNS})... `);
        const r = await timeRun(detected[name], target, i);
        allResults.push(r);
        const mark = r.success ? '✅' : '❌';
        console.log(`${mark} ${r.time_ms}ms (${r.size}B, status ${r.status})`);
      }
    }
  }

  // ===== CSV =====
  const headers = ['lib', 'target', 'run', 'success', 'status', 'size', 'time_ms', 'ua', 'error'];
  const csv = [headers.join(',')].concat(
    allResults.map(r => headers.map(h => {
      const v = r[h];
      if (v === null || v === undefined) return '';
      const s = String(v).replace(/"/g, '""');
      return /[,"\n]/.test(s) ? `"${s}"` : s;
    }).join(','))
  ).join('\n');
  fs.writeFileSync(CSV_PATH, csv);

  // ===== Summary =====
  const summary = {};
  for (const r of allResults) {
    const key = r.lib;
    if (!summary[key]) summary[key] = { runs: 0, success: 0, total_time: 0, total_size: 0, errors: [] };
    summary[key].runs++;
    if (r.success) summary[key].success++;
    summary[key].total_time += r.time_ms;
    summary[key].total_size += r.size;
    if (r.error) summary[key].errors.push(r.error);
  }

  // ===== Markdown =====
  let md = `# Benchmark Report — ${TIMESTAMP}\n\n`;
  md += `**Targets:** ${TARGETS.length} | **Runs/target/lib:** ${RUNS}\n\n`;
  md += `## Summary\n\n| Lib | Success Rate | Avg Time | Avg Size | Version |\n`;
  md += `|-----|--------------|----------|----------|---------|\n`;
  for (const [lib, s] of Object.entries(summary)) {
    const rate = ((s.success / s.runs) * 100).toFixed(1);
    const avgTime = (s.total_time / s.runs).toFixed(0);
    const avgSize = Math.round(s.total_size / s.runs);
    const ver = detected[lib].ok ? detected[lib].version : '—';
    md += `| ${lib} | ${s.success}/${s.runs} (${rate}%) | ${avgTime}ms | ${avgSize}B | ${ver} |\n`;
  }
  md += `\n## Verdict\n\n`;
  const patchright = summary.patchright || { success: 0, runs: 1, total_time: 0 };
  const playwright = summary.playwright || { success: 0, runs: 1, total_time: 0 };
  const prRate = patchright.success / patchright.runs;
  const pwRate = playwright.success / playwright.runs;
  if (prRate > pwRate) {
    md += `🏆 **patchright wins** (${(prRate*100).toFixed(0)}% vs ${(pwRate*100).toFixed(0)}%)\n`;
  } else if (pwRate > prRate) {
    md += `🏆 **playwright wins** (${(pwRate*100).toFixed(0)}% vs ${(prRate*100).toFixed(0)}%)\n`;
  } else {
    md += `🤝 **Tie** (both at ${(prRate*100).toFixed(0)}%)\n`;
  }
  md += `\n## Per-target\n\n`;
  const byTarget = {};
  for (const r of allResults) {
    if (!byTarget[r.target]) byTarget[r.target] = {};
    if (!byTarget[r.target][r.lib]) byTarget[r.target][r.lib] = { runs: 0, success: 0, total_time: 0 };
    const s = byTarget[r.target][r.lib];
    s.runs++;
    if (r.success) s.success++;
    s.total_time += r.time_ms;
  }
  md += `| Target | patchright | playwright |\n|--------|------------|-----------|\n`;
  for (const [t, libs] of Object.entries(byTarget)) {
    const pr = libs.patchright ? `${libs.patchright.success}/${libs.patchright.runs} (${(libs.patchright.total_time/libs.patchright.runs).toFixed(0)}ms)` : '—';
    const pw = libs.playwright ? `${libs.playwright.success}/${libs.playwright.runs} (${(libs.playwright.total_time/libs.playwright.runs).toFixed(0)}ms)` : '—';
    md += `| ${t} | ${pr} | ${pw} |\n`;
  }
  md += `\n## Errors\n\n`;
  for (const [lib, s] of Object.entries(summary)) {
    if (s.errors.length === 0) continue;
    md += `### ${lib}\n`;
    const uniq = [...new Set(s.errors)];
    for (const e of uniq.slice(0, 5)) md += `- ${e}\n`;
  }
  md += `\n## Files\n- CSV: ${CSV_PATH}\n- MD: ${MD_PATH}\n`;
  fs.writeFileSync(MD_PATH, md);

  console.log('\n📊 Summary:');
  for (const [lib, s] of Object.entries(summary)) {
    const rate = ((s.success / s.runs) * 100).toFixed(0);
    console.log(`   ${lib.padEnd(11)} ${s.success}/${s.runs} (${rate}%) avg ${(s.total_time/s.runs).toFixed(0)}ms`);
  }
  console.log(`\n📄 CSV: ${CSV_PATH}`);
  console.log(`📄 MD:  ${MD_PATH}`);
})().catch(e => {
  console.error('💥 Fatal:', e);
  process.exit(1);
});
