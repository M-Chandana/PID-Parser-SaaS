const axios = require('axios');

const BACKEND_BASE_URL = process.env.BACKEND_BASE_URL || 'http://127.0.0.1:5000';

async function postWebhook(payload) {
  return axios.post(`${BACKEND_BASE_URL}/api/webhooks/stripe`, payload, {
    headers: { 'Content-Type': 'application/json' },
    validateStatus: () => true,
    timeout: 5000,
  });
}

async function main() {
  console.log('=== B4 Webhook Negative Verification ===');
  console.log(`Timestamp: ${new Date().toISOString()}`);

  const invalidPlanPayload = {
    eventType: 'checkout.session.completed',
    userEmail: 'negative_plan_test@example.com',
    planName: 'not-a-real-plan',
  };

  const invalidPlanRes = await postWebhook(invalidPlanPayload);
  console.log('Invalid plan response:', invalidPlanRes.status, invalidPlanRes.data);

  if (invalidPlanRes.status !== 404) {
    throw new Error(`Expected 404 for invalid plan, got ${invalidPlanRes.status}`);
  }

  const unknownUserPayload = {
    eventType: 'subscription.updated',
    userEmail: `unknown_${Date.now()}@example.com`,
    planName: 'paid',
  };

  const unknownUserRes = await postWebhook(unknownUserPayload);
  console.log('Unknown user response:', unknownUserRes.status, unknownUserRes.data);

  if (unknownUserRes.status !== 404) {
    throw new Error(`Expected 404 for unknown user, got ${unknownUserRes.status}`);
  }

  console.log('Webhook negative verification passed.');
}

main().catch((error) => {
  console.error('Webhook negative verification failed:', error.message);
  process.exit(1);
});
