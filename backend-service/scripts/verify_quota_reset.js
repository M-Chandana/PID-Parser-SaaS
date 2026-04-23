const axios = require('axios');
const path = require('path');
const fs = require('fs');
const FormData = require('form-data');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();
const BASE_URL = process.env.BACKEND_BASE_URL || 'http://127.0.0.1:5000/api';
const FILE_PATH = process.env.QUOTA_TEST_FILE || path.resolve(__dirname, '..', '..', 'ai-service', 'test_pid.png');

async function signup(email, password) {
  const response = await axios.post(`${BASE_URL}/auth/signup`, { email, password });
  return response.data.token;
}

async function upload(token) {
  const form = new FormData();
  form.append('file', fs.createReadStream(FILE_PATH));

  try {
    const response = await axios.post(`${BASE_URL}/jobs`, form, {
      headers: {
        Authorization: `Bearer ${token}`,
        ...form.getHeaders(),
      },
      timeout: 30000,
    });

    return { status: response.status, data: response.data };
  } catch (error) {
    if (error.response) {
      return { status: error.response.status, data: error.response.data };
    }
    throw error;
  }
}

async function main() {
  console.log('=== B4 Quota Reset Verification ===');
  console.log(`Timestamp: ${new Date().toISOString()}`);

  const email = `quota_reset_${Date.now()}@example.com`;
  const password = 'password123';
  const token = await signup(email, password);

  console.log(`Created free user: ${email}`);

  for (let i = 1; i <= 5; i += 1) {
    const result = await upload(token);
    if (result.status !== 201) {
      throw new Error(`Expected upload #${i} status 201, got ${result.status}`);
    }
    console.log(`Upload #${i}: ${result.status}`);
  }

  const blocked = await upload(token);
  console.log('Upload #6 (expected block):', blocked.status, blocked.data);
  if (blocked.status !== 429) {
    throw new Error(`Expected 429 on upload #6, got ${blocked.status}`);
  }

  const user = await prisma.user.findUnique({ where: { email } });
  if (!user) {
    throw new Error('Quota test user not found in DB');
  }

  const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
  await prisma.user.update({
    where: { id: user.id },
    data: { lastResetDate: yesterday },
  });

  const afterReset = await upload(token);
  console.log('Upload after simulated day rollover:', afterReset.status);
  if (afterReset.status !== 201) {
    throw new Error(`Expected 201 after reset simulation, got ${afterReset.status}`);
  }

  console.log('Quota reset verification passed.');
}

main()
  .catch((error) => {
    console.error('Quota reset verification failed:', error.message);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
