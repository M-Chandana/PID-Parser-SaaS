const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const prisma = require('../db');
const { authenticateToken } = require('../middlewares/auth');
const { checkQuota } = require('../middlewares/quota');
const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');

// Multer config for file upload (Max 5MB) - use memory storage so we can optionally upload to S3
const storage = multer.memoryStorage();

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

    // Persist file either to S3 (if configured) or to local storage
    let storedPath = null;
    const storageDir = process.env.STORAGE_DIR || './storage';

    if (process.env.S3_BUCKET && process.env.AWS_REGION) {
      const s3 = new S3Client({ region: process.env.AWS_REGION });
      const key = `${Date.now()}-${Math.round(Math.random() * 1E9)}${path.extname(req.file.originalname)}`;
      const params = {
        Bucket: process.env.S3_BUCKET,
        Key: key,
        Body: req.file.buffer,
        ContentType: req.file.mimetype
      };
      try {
        await s3.send(new PutObjectCommand(params));
        storedPath = `https://${process.env.S3_BUCKET}.s3.amazonaws.com/${encodeURIComponent(key)}`;
      } catch (s3err) {
        console.error('S3 upload error:', s3err);
        return res.status(500).json({ error: 'Failed to store file in object storage' });
      }
    } else {
      // Fallback to local storage
      if (!fs.existsSync(storageDir)) fs.mkdirSync(storageDir, { recursive: true });
      const filename = `${Date.now()}-${Math.round(Math.random() * 1E9)}${path.extname(req.file.originalname)}`;
      const filepath = path.join(storageDir, filename);
      fs.writeFileSync(filepath, req.file.buffer);
      storedPath = filepath;
    }

    const job = await prisma.job.create({
      data: {
        userId,
        status: 'queued',
        originalFile: storedPath,
        fileSize: req.file.size
      }
    });

    // The job is queued for later processing.
    res.status(201).json(job);
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ error: 'Failed to create job' });
  }
});

module.exports = router;
