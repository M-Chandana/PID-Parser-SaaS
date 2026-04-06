const fs = require('fs');
const path = require('path');
const axios = require('axios');
const FormData = require('form-data');
const prisma = require('./db');
const dotenv = require('dotenv');

dotenv.config();

// Configuration
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000/parse';
const POLLING_INTERVAL = 3000; 
const MAX_FILE_SIZE_MB = 5;
const STORAGE_DIR = path.resolve(process.env.STORAGE_DIR || './storage');
const SECRET_API_KEY = process.env.SECRET_API_KEY || 'pid-parser-internal-secret-2026';

/**
 * Main worker loop
 */
async function worker() {
  console.log(`[Worker] B3 Pipeline Runner: Fully Secured Mode Started...`);
  console.log(`[Worker] Storage Sandbox: ${STORAGE_DIR}`);
  
  while (true) {
    try {
      // 1. Fetch next queued job (Priority to 'paid' users)
      const job = await prisma.job.findFirst({
        where: { status: 'queued' },
        orderBy: [
          { user: { plan: { name: 'desc' } } }, 
          { createdAt: 'asc' } 
        ],
        include: { user: { include: { plan: true } } }
      });

      if (!job) {
        await new Promise(resolve => setTimeout(resolve, POLLING_INTERVAL));
        continue;
      }

      console.log(`[Worker] [Job:${job.id}] Picking up for ${job.user.email} (${job.user.plan.name})`);
      
      // 2. Mark as processing
      await prisma.job.update({
        where: { id: job.id },
        data: { status: 'processing', updatedAt: new Date() }
      });

      // 3. Process with Retry Logic
      let result;
      let attempt = 1;
      const MAX_ATTEMPTS = 2;

      while (attempt <= MAX_ATTEMPTS) {
        try {
          const startTime = Date.now();
          result = await processAIDetection(job);
          const processingTime = (Date.now() - startTime) / 1000;

          // 4. Save Artifacts
          await saveResults(job.id, result, processingTime);
          console.log(`[Worker] [Job:${job.id}] COMPLETED in ${processingTime}s`);
          break; 

        } catch (err) {
          console.error(`[Worker] [Job:${job.id}] Attempt ${attempt} FAILED:`, err.message);
          
          if (attempt === MAX_ATTEMPTS) {
            await prisma.job.update({
              where: { id: job.id },
              data: { 
                status: 'failed', 
                error: `Final attempt failed: ${err.message}`,
                updatedAt: new Date() 
              }
            });
          } else {
            console.log(`[Worker] [Job:${job.id}] Retrying in 2 seconds...`);
            await new Promise(r => setTimeout(r, 2000));
          }
        }
        attempt++;
      }

    } catch (error) {
      console.error('[Worker] Unexpected system loop error:', error);
      await new Promise(resolve => setTimeout(resolve, POLLING_INTERVAL));
    }
  }
}

/**
 * Validates file and sends it to the B1 AI Service with Security Headers
 */
async function processAIDetection(job) {
  const filePath = path.resolve(job.originalFile);
  
  // SECURITY: Path Sandboxing (Mandatory for B3 Security)
  // Ensure the resolved path starts with the STORAGE_DIR path
  if (!filePath.startsWith(STORAGE_DIR)) {
    throw new Error(`SECURITY ALERT: Path Traversal detected. Attempted to read outside storage: ${filePath}`);
  }

  if (!fs.existsSync(filePath)) {
    throw new Error(`File not found at: ${filePath}`);
  }

  // File Type & Size Validation
  const stats = fs.statSync(filePath);
  const sizeMB = stats.size / (1024 * 1024);
  const ext = path.extname(filePath).toLowerCase();
  const allowedExts = ['.pdf', '.jpg', '.jpeg', '.png'];

  if (sizeMB > MAX_FILE_SIZE_MB) {
    throw new Error(`File exceeds ${MAX_FILE_SIZE_MB}MB limit`);
  }
  if (!allowedExts.includes(ext)) {
    throw new Error(`Unsupported file type: ${ext}`);
  }

  // API Call with Authentication Header
  const formData = new FormData();
  formData.append('file', fs.createReadStream(filePath));

  const response = await axios.post(AI_SERVICE_URL, formData, {
    headers: { 
      ...formData.getHeaders(),
      'X-API-Key': SECRET_API_KEY // Security: Shared Secret Auth
    },
    timeout: 300000 
  });

  return response.data;
}

/**
 * Atomic Result Storage
 */
async function saveResults(jobId, result, procTime) {
  await prisma.$transaction([
    prisma.artifact.create({
      data: {
        jobId,
        name: 'full_parse_result',
        path: JSON.stringify(result) 
      }
    }),
    prisma.job.update({
      where: { id: jobId },
      data: { 
        status: 'completed', 
        processingTime: procTime,
        updatedAt: new Date() 
      }
    })
  ]);
}

worker();
