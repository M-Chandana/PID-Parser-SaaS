const prisma = require('../db');

const checkQuota = async (req, res, next) => {
  try {
    const userId = req.user.id;
    const user = await prisma.user.findUnique({ where: { id: userId } });
    if (!user) return res.status(404).json({ error: 'User not found' });

    const now = new Date();
    const lastReset = user.lastResetDate;

    // Determine if counters need resetting based on plan types
    const isFree = user.planType === 'free';
    
    // For free plan, reset daily. For paid plan, reset monthly.
    let needsReset = false;
    if (isFree) {
      if (now.getDate() !== lastReset.getDate() || now.getMonth() !== lastReset.getMonth() || now.getFullYear() !== lastReset.getFullYear()) {
        needsReset = true;
      }
    } else { // paid
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

    // Check limits
    if (isFree && user.dailyUsage >= 5) {
      return res.status(429).json({ error: 'Free plan quota exceeded (5 files/day). Please upgrade.' });
    } else if (!isFree && user.monthlyUsage >= 1000) {
       return res.status(429).json({ error: 'Paid plan quota exceeded (1000 files/month).' });
    }

    // Attach user to req context for subsequent use if needed
    req.dbUser = user;
    next();
  } catch (error) {
    console.error('Quota check failed', error);
    res.status(500).json({ error: 'Failed to verify usage quota' });
  }
};

module.exports = { checkQuota };
