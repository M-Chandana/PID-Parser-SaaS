const axios = require('axios');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || 'http://127.0.0.1:5000';
const AI_HEALTH_URL = process.env.AI_HEALTH_URL || 'http://127.0.0.1:8000/health';

async function checkBackendHealth() {
  const url = `${BACKEND_BASE_URL}/api/health`;
  const response = await axios.get(url, { timeout: 5000 });
  return { url, data: response.data };
}

async function checkAiHealth() {
  const response = await axios.get(AI_HEALTH_URL, { timeout: 5000 });
  return { url: AI_HEALTH_URL, data: response.data };
}

async function checkDbHealth() {
  // Minimal DB liveness check through Prisma
  await prisma.$queryRaw`SELECT 1`;
  return { query: 'SELECT 1', status: 'ok' };
}

async function main() {
  console.log('=== B4 Health Verification ===');
  console.log(`Timestamp: ${new Date().toISOString()}`);

  const results = {
    backend: null,
    ai: null,
    db: null,
    overall: 'ok',
  };

  try {
    results.backend = await checkBackendHealth();
    console.log('[OK] Backend health:', results.backend);
  } catch (error) {
    results.overall = 'failed';
    console.error('[FAIL] Backend health check failed:', error.message);
  }

  try {
    results.ai = await checkAiHealth();
    console.log('[OK] AI health:', results.ai);
  } catch (error) {
    results.overall = 'failed';
    console.error('[FAIL] AI health check failed:', error.message);
  }

  try {
    results.db = await checkDbHealth();
    console.log('[OK] DB health:', results.db);
  } catch (error) {
    results.overall = 'failed';
    console.error('[FAIL] DB health check failed:', error.message);
  }

  await prisma.$disconnect();

  if (results.overall !== 'ok') {
    process.exitCode = 1;
  }
}

main().catch(async (error) => {
  console.error('Unexpected health verification error:', error);
  await prisma.$disconnect();
  process.exit(1);
});
