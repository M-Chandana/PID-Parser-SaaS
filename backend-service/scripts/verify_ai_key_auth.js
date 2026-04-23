const axios = require('axios');
const fs = require('fs');
const path = require('path');
const FormData = require('form-data');

const AI_PARSE_URL = process.env.AI_PARSE_URL || 'http://127.0.0.1:8000/parse';
const FILE_PATH = process.env.KEY_AUTH_TEST_FILE || path.resolve(__dirname, '..', '..', 'ai-service', 'test_pid.png');
const CORRECT_KEY = process.env.SECRET_API_KEY || 'pid-parser-internal-secret-2026';

async function parseWithKey(key) {
  const form = new FormData();
  form.append('file', fs.createReadStream(FILE_PATH));

  const response = await axios.post(AI_PARSE_URL, form, {
    headers: {
      ...form.getHeaders(),
      'X-API-Key': key,
    },
    validateStatus: () => true,
    timeout: 60000,
  });

  return response;
}

async function main() {
  console.log('=== B4 AI Key Auth Verification ===');
  console.log(`Timestamp: ${new Date().toISOString()}`);

  const wrong = await parseWithKey('wrong-key-for-b4-check');
  console.log('Wrong key status:', wrong.status);
  if (wrong.status !== 403) {
    throw new Error(`Expected 403 for wrong key, got ${wrong.status}`);
  }

  const correct = await parseWithKey(CORRECT_KEY);
  console.log('Correct key status:', correct.status);
  if (correct.status !== 200) {
    throw new Error(`Expected 200 for correct key, got ${correct.status}`);
  }

  console.log('AI key auth verification passed.');
}

main().catch((error) => {
  console.error('AI key auth verification failed:', error.message);
  process.exit(1);
});
