const express = require('express');
const router = express.Router();
const prisma = require('../db');
const Stripe = require('stripe');

const stripeSecret = process.env.STRIPE_SECRET || '';
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET || '';

let stripe = null;
if (stripeSecret) stripe = new Stripe(stripeSecret, { apiVersion: '2022-11-15' });

// POST /api/webhooks/stripe -> verify signature and update subscription
router.post('/stripe', async (req, res) => {
  // Expect raw body parsing to be done by index.js for this route
  const sig = req.headers['stripe-signature'];
  let event = null;

  try {
    if (webhookSecret && stripe) {
      event = stripe.webhooks.constructEvent(req.rawBody, sig, webhookSecret);
    } else {
      // If no webhook secret configured, fall back to simple JSON body (unsafe)
      event = req.body;
    }
  } catch (err) {
    console.error('Webhook signature verification failed:', err.message);
    return res.status(400).json({ error: 'Webhook signature verification failed' });
  }

  try {
    const type = event.type || event.eventType || '';
    if (type === 'checkout.session.completed' || type === 'checkout.session.completed') {
      const email = event.data?.object?.customer_email || event.data?.object?.customer || (req.body && req.body.userEmail);
      if (email) {
        const user = await prisma.user.findUnique({ where: { email } });
        if (user) {
          const paidPlan = await prisma.plan.findUnique({ where: { name: 'paid' } });
          if (paidPlan) {
            await prisma.user.update({ where: { id: user.id }, data: { planId: paidPlan.id, monthlyUsage: 0 } });
          }
        }
      }
    }

    res.json({ received: true });
  } catch (err) {
    console.error('Webhook processing error:', err);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
});

module.exports = router;
