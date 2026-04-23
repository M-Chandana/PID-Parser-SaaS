const axios = require('axios');
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || 'http://127.0.0.1:5000';
const TEST_USER_EMAIL = process.env.TEST_USER_EMAIL;

if (!TEST_USER_EMAIL) {
  console.error('Missing TEST_USER_EMAIL environment variable.');
  process.exit(1);
}

async function getUserPlan(email) {
  const user = await prisma.user.findUnique({
    where: { email },
    include: { plan: true },
  });

  if (!user) {
    throw new Error(`User not found for email: ${email}`);
  }

  return { id: user.id, email: user.email, plan: user.plan.name };
}

async function callWebhook(eventType, planName = 'paid') {
  const url = `${BACKEND_BASE_URL}/api/webhooks/stripe`;
  const payload = {
    eventType,
    userEmail: TEST_USER_EMAIL,
    planName,
  };

  const response = await axios.post(url, payload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: 5000,
  });

  return { status: response.status, data: response.data };
}

async function main() {
  console.log('=== B4 Webhook Verification (Staging) ===');
  console.log(`Timestamp: ${new Date().toISOString()}`);
  console.log(`Target user: ${TEST_USER_EMAIL}`);

  const before = await getUserPlan(TEST_USER_EMAIL);
  console.log('Before:', before);

  const checkoutResult = await callWebhook('checkout.session.completed', 'paid');
  console.log('checkout.session.completed ->', checkoutResult);

  const afterCheckout = await getUserPlan(TEST_USER_EMAIL);
  console.log('After checkout event:', afterCheckout);

  const updateResult = await callWebhook('subscription.updated', 'paid');
  console.log('subscription.updated ->', updateResult);

  const afterUpdate = await getUserPlan(TEST_USER_EMAIL);
  console.log('After subscription update event:', afterUpdate);

  console.log('Webhook verification completed.');
  await prisma.$disconnect();
}

main().catch(async (error) => {
  console.error('Webhook verification failed:', error.message);
  await prisma.$disconnect();
  process.exit(1);
});
