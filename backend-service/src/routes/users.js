const express = require('express');
const router = express.Router();
const prisma = require('../db');
const { authenticateToken } = require('../middlewares/auth');

// GET /api/users/me -> get user profile & limits
router.get('/me', authenticateToken, async (req, res) => {
  try {
    const user = await prisma.user.findUnique({ 
      where: { id: req.user.id },
      include: {
        plan: true
      }
    });

    if (!user) return res.status(404).json({ error: 'User not found' });
    
    // Format response to provide plan name clearly
    const userData = {
      ...user,
      planName: user.plan.name,
      maxDaily: user.plan.maxDaily,
      maxMonthly: user.plan.maxMonthly
    };
    delete userData.plan; // cleanup raw object
    delete userData.passwordHash;

    res.json(userData);
  } catch (error) {
    console.error('Error fetching user:', error);
    res.status(500).json({ error: 'Failed to fetch user' });
  }
});

// POST /api/users/upgrade -> Mock upgrade subscription
router.post('/upgrade', authenticateToken, async (req, res) => {
  try {
    const paidPlan = await prisma.plan.findUnique({ where: { name: 'paid' } });
    if (!paidPlan) return res.status(500).json({ error: 'System error: Paid plan not found. Please run seeding.' });

    const updatedUser = await prisma.user.update({
      where: { id: req.user.id },
      data: { planId: paidPlan.id, monthlyUsage: 0, lastResetDate: new Date() },
      include: { plan: true }
    });
    
    res.json({ id: updatedUser.id, email: updatedUser.email, plan: updatedUser.plan.name });
  } catch (error) {
    console.error('Upgrade error:', error);
    res.status(500).json({ error: 'Failed to upgrade plan' });
  }
});

module.exports = router;
