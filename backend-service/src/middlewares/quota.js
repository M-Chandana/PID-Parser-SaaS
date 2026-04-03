const prisma = require('../db');

const checkQuota = async (req, res, next) => {
  try {
    const userId = req.user.id;
    // Fetch user including their plan details
    const user = await prisma.user.findUnique({ 
      where: { id: userId },
      include: { plan: true } 
    });

    if (!user) return res.status(404).json({ error: 'User not found' });

    const now = new Date();
    const lastReset = user.lastResetDate;

    // Determine if counters need resetting based on plan types
    // For free plan, reset daily. For paid plan, reset monthly.
    let needsReset = false;
    if (user.plan.name === 'free') {
      if (now.getDate() !== lastReset.getDate() || now.getMonth() !== lastReset.getMonth() || now.getFullYear() !== lastReset.getFullYear()) {
        needsReset = true;
      }
    } else { // paid/pro
      if (now.getMonth() !== lastReset.getMonth() || now.getFullYear() !== lastReset.getFullYear()) {
        needsReset = true;
      }
    }

    if (needsReset) {
      await prisma.user.update({
        where: { id: userId },
        data: {
          dailyUsage: 0,
          monthlyUsage: 0,
          lastResetDate: now
        }
      });
      user.dailyUsage = 0;
      user.monthlyUsage = 0;
    }

    // Check limits using values from the Plan table
    if (user.plan.name === 'free' && user.dailyUsage >= user.plan.maxDaily) {
      return res.status(429).json({ 
        error: `Free plan quota exceeded (${user.plan.maxDaily} files/day). Please upgrade.` 
      });
    } else if (user.plan.name !== 'free' && user.monthlyUsage >= user.plan.maxMonthly) {
       return res.status(429).json({ 
         error: `Plan quota exceeded (${user.plan.maxMonthly} files/month).` 
       });
    }

    // Attach user and plan details for subsequent use
    req.dbUser = user;
    next();
  } catch (error) {
    console.error('Quota check failed', error);
    res.status(500).json({ error: 'Failed to verify usage quota' });
  }
};

module.exports = { checkQuota };
