const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const prisma = require('../db');
const { authenticateToken } = require('../middlewares/auth');
const { checkQuota } = require('../middlewares/quota');

// Multer config for file upload (Max 5MB)
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, process.env.STORAGE_DIR || './storage');
  },
  filename: (req, file, cb) => {
    // Unique filename
    cb(null, `${Date.now()}-${Math.round(Math.random() * 1E9)}${path.extname(file.originalname)}`);
  }
});

const fileFilter = (req, file, cb) => {
  const allowedTypes = ['.pdf', '.jpg', '.jpeg', '.png'];
  const ext = path.extname(file.originalname).toLowerCase();
  if (allowedTypes.includes(ext)) {
    cb(null, true);
  } else {
    cb(new Error(`Invalid file type. Allowed: ${allowedTypes.join(', ')}`));
  }
};

const upload = multer({ 
  storage,
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB limit
  fileFilter
});

// GET /api/jobs -> list user's jobs
router.get('/', authenticateToken, async (req, res) => {
  try {
    const jobs = await prisma.job.findMany({
      where: { userId: req.user.id },
      orderBy: { createdAt: 'desc' },
      include: { artifacts: true }
    });
    res.json(jobs);
  } catch (error) {
    console.error('Error fetching jobs:', error);
    res.status(500).json({ error: 'Failed to fetch jobs' });
  }
});

// GET /api/jobs/:id -> get specific job
router.get('/:id', authenticateToken, async (req, res) => {
  try {
    const job = await prisma.job.findUnique({
      where: { id: req.params.id },
      include: { artifacts: true }
    });
    if (!job || job.userId !== req.user.id) {
      return res.status(404).json({ error: 'Job not found' });
    }
    res.json(job);
  } catch (error) {
    console.error('Error fetching job:', error);
    res.status(500).json({ error: 'Failed to fetch job' });
  }
});

// POST /api/jobs -> upload file, check quota, create job
router.post('/', authenticateToken, checkQuota, upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No file uploaded' });
    }

    const userId = req.user.id;
    const isFree = req.dbUser.plan && req.dbUser.plan.name === 'free';
    
    // Increment usage
    await prisma.user.update({
      where: { id: userId },
      data: {
        dailyUsage: { increment: isFree ? 1 : 0 },
        monthlyUsage: { increment: !isFree ? 1 : 0 }
      }
    });

    const job = await prisma.job.create({
      data: {
        userId,
        status: 'queued',
        originalFile: req.file.path,
        fileSize: req.file.size
      }
    });

    // In an ideal B3 scenario, a worker process picks this up.
    // For now, we return successfully. The worker will handle AI processing.
    res.status(201).json(job);
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to create job' });
  }
});

module.exports = router;
