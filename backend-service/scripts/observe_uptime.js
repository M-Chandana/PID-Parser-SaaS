const axios = require('axios');

const BACKEND_HEALTH_URL = process.env.BACKEND_HEALTH_URL || 'http://127.0.0.1:5000/api/health';
const AI_HEALTH_URL = process.env.AI_HEALTH_URL || 'http://127.0.0.1:8000/health';
const DURATION_SECONDS = Number(process.env.UPTIME_DURATION_SECONDS || 60);
const INTERVAL_SECONDS = Number(process.env.UPTIME_INTERVAL_SECONDS || 10);
const HEALTH_TIMEOUT_MS = Number(process.env.UPTIME_HEALTH_TIMEOUT_MS || 10000);

async function check(url) {
  const response = await axios.get(url, { timeout: HEALTH_TIMEOUT_MS });
  return response.status >= 200 && response.status < 300;
}

async function checkWithRetry(url) {
  try {
    return await check(url);
  } catch (_) {
    await sleep(1000);
    return check(url);
  }
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  console.log('=== B4 Uptime Observation ===');
  console.log(`Start: ${new Date().toISOString()}`);
  console.log(`Duration(s): ${DURATION_SECONDS}, Interval(s): ${INTERVAL_SECONDS}`);

  const endTime = Date.now() + DURATION_SECONDS * 1000;
  let passCount = 0;
  let failCount = 0;

  while (Date.now() < endTime) {
    const ts = new Date().toISOString();

    try {
      const backendOk = await checkWithRetry(BACKEND_HEALTH_URL);
      const aiOk = await checkWithRetry(AI_HEALTH_URL);
      if (backendOk && aiOk) {
        passCount += 1;
        console.log(`[PASS] ${ts} backend+ai healthy`);
      } else {
        failCount += 1;
        console.log(`[FAIL] ${ts} unhealthy response`);
      }
    } catch (error) {
      failCount += 1;
      console.log(`[FAIL] ${ts} ${error.message}`);
    }

    await sleep(INTERVAL_SECONDS * 1000);
  }

  console.log(`End: ${new Date().toISOString()}`);
  console.log(`Pass checks: ${passCount}`);
  console.log(`Fail checks: ${failCount}`);

  if (failCount > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error('Uptime observation failed:', error.message);
  process.exit(1);
});
