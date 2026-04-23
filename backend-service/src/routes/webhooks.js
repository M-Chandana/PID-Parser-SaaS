const express = require('express');
const router = express.Router();
const prisma = require('../db');

// POST /api/webhooks/stripe
// This is a placeholder for Stripe payment webhooks.
// When a payment is successful, we upgrade the user's plan.
router.post('/stripe', async (req, res) => {
  const { eventType, userEmail, planName } = req.body;

  console.log(`Received webhook: ${eventType} for ${userEmail}`);

  try {
    const supportedEvents = ['checkout.session.completed', 'subscription.updated'];

    if (!supportedEvents.includes(eventType)) {
      return res.json({ received: true, ignored: true, reason: 'Unsupported event type' });
    }

    if (!userEmail) {
      return res.status(400).json({ error: 'Missing userEmail in webhook payload' });
    }

    const targetPlanName = planName || 'paid';
    const plan = await prisma.plan.findUnique({ where: { name: targetPlanName } });

    if (!plan) {
      return res.status(404).json({ error: `Plan not found: ${targetPlanName}` });
    }

    const user = await prisma.user.findUnique({ where: { email: userEmail } });
    if (!user) {
      return res.status(404).json({ error: `User not found: ${userEmail}` });
    }

    await prisma.user.update({
      where: { id: user.id },
      data: { planId: plan.id }
    });

    console.log(`User ${userEmail} upgraded to ${plan.name} plan`);

    res.json({ received: true });
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
});

module.exports = router;
