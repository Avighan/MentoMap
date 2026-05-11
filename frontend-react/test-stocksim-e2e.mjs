// frontend-react/test-stocksim-e2e.mjs
// Run: BASE=http://localhost:5001 USER=demo_student PASS=Mento@2026 node test-stocksim-e2e.mjs
const BASE = process.env.BASE || 'http://localhost:5001';
const USERNAME = process.env.USER || 'demo_student';
const PASSWORD = process.env.PASS || 'Mento@2026';

async function login() {
  const r = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: USERNAME, password: PASSWORD }),
  });
  if (!r.ok) throw new Error(`login failed: ${r.status} ${await r.text()}`);
  const body = await r.json();
  const token = body.access_token || body.token || body.jwt;
  if (!token) throw new Error(`no token in login response: ${JSON.stringify(body)}`);
  return token;
}

async function main() {
  console.log(`▶ stocksim E2E against ${BASE} as ${USERNAME}`);
  const token = await login();
  const auth = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  // Start a run for the day-trader game
  const startRun = await fetch(`${BASE}/api/run/start`, {
    method: 'POST',
    headers: auth,
    body: JSON.stringify({ game_id: 'stock-market-day-trader' }),
  });
  if (!startRun.ok) throw new Error(`run/start failed: ${startRun.status} ${await startRun.text()}`);
  const runBody = await startRun.json();
  const runId = runBody.run_id || runBody.runId || runBody.id;
  if (!runId) throw new Error(`no run_id in response: ${JSON.stringify(runBody)}`);
  console.log(`  run_id: ${runId}`);

  // Start the stocksim session
  const startSim = await fetch(`${BASE}/api/run/${runId}/stocksim/start`, {
    method: 'POST',
    headers: auth,
    body: '{}',
  });
  if (!startSim.ok) throw new Error(`stocksim/start failed: ${startSim.status} ${await startSim.text()}`);
  const simBody = await startSim.json();
  console.log(`  stocksim seed: ${simBody.seed}, ticks: ${simBody.config?.tick_count}`);

  // Place 3 trades
  const trades = [
    { tick: 1,  symbol: 'TECHV',  side: 'buy',  qty: 5,  order_type: 'market' },
    { tick: 4,  symbol: 'GREENX', side: 'buy',  qty: 10, order_type: 'limit', limit_price: 420 },
    { tick: 18, symbol: 'TECHV', side: 'sell', qty: 5,  order_type: 'market' },
  ];
  for (const t of trades) {
    const r = await fetch(`${BASE}/api/run/${runId}/stocksim/trade`, {
      method: 'POST',
      headers: auth,
      body: JSON.stringify(t),
    });
    const body = r.ok ? await r.json() : await r.text();
    console.log(`  trade ${t.side} ${t.symbol} qty=${t.qty} @ tick=${t.tick} → ${r.status} ${typeof body === 'object' ? body.status : body}`);
  }

  // Complete the session
  const complete = await fetch(`${BASE}/api/run/${runId}/stocksim/complete`, {
    method: 'POST',
    headers: auth,
    body: '{}',
  });
  if (!complete.ok) throw new Error(`stocksim/complete failed: ${complete.status} ${await complete.text()}`);
  const final = await complete.json();
  console.log(`  pnl: ${JSON.stringify(final.pnl)}`);
  console.log(`  dimensions: ${JSON.stringify(final.dimensions)}`);
  console.log(`  recap: ${JSON.stringify(final.recap_messages)}`);

  // Validate response shape
  if (!final.pnl || typeof final.pnl.total !== 'number') {
    throw new Error(`pnl.total missing or not a number: ${JSON.stringify(final.pnl)}`);
  }
  if (!final.dimensions || typeof final.dimensions !== 'object') {
    throw new Error(`dimensions missing: ${JSON.stringify(final.dimensions)}`);
  }
  const requiredDims = ['risk_tolerance', 'delayed_gratification', 'strategic_thinking', 'financial_literacy'];
  for (const d of requiredDims) {
    if (typeof final.dimensions[d] !== 'number') {
      throw new Error(`dimension ${d} missing or not a number: ${JSON.stringify(final.dimensions)}`);
    }
  }

  // v2 assertion: trade_log_enriched present on /complete (Task 12).
  if (!Array.isArray(final.trade_log_enriched)) {
    throw new Error(`trade_log_enriched missing on /complete: ${JSON.stringify(Object.keys(final))}`);
  }
  console.log(`  v2: trade_log_enriched length: ${final.trade_log_enriched.length}`);

  // Idempotency check: complete again, expect same shape
  const complete2 = await fetch(`${BASE}/api/run/${runId}/stocksim/complete`, {
    method: 'POST',
    headers: auth,
    body: '{}',
  });
  if (!complete2.ok) throw new Error(`second complete failed: ${complete2.status}`);
  const final2 = await complete2.json();
  if (final2.pnl?.total !== final.pnl.total) {
    throw new Error(`complete is not idempotent: ${final.pnl.total} vs ${final2.pnl?.total}`);
  }

  console.log('✅ stocksim E2E smoke passed');
}

main().catch((e) => { console.error('❌', e.message); process.exit(1); });
