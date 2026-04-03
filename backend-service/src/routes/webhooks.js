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
    if (eventType === 'checkout.session.completed' || eventType === 'subscription.updated') {
      const plan = await prisma.plan.findUnique({ where: { name: planName || 'paid' } });
      
      if (!plan) {
        return res.status(404).json({ error: 'Plan not found' });
      }

      await prisma.user.update({
        where: { email: userEmail },
        data: { planId: plan.id }
      });

      console.log(`User ${userEmail} upgraded to ${plan.name} plan`);
    }

    res.json({ received: true });
  } catch (error) {
    console.error('Webhook error:', error);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
});

module.exports = router;
