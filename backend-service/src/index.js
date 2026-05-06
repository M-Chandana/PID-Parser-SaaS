const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const fs = require('fs');

dotenv.config();

const authRoutes = require('./routes/auth');
const jobRoutes = require('./routes/jobs');
const userRoutes = require('./routes/users');
const webhookRoutes = require('./routes/webhooks');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Ensure storage directory exists (mock object storage for phase 1)
const storageDir = process.env.STORAGE_DIR || './storage';
if (!fs.existsSync(storageDir)) {
  fs.mkdirSync(storageDir, { recursive: true });
}
// Serve storage files statically so frontend can visualize them
app.use('/storage', express.static(storageDir));

// Routes
app.use('/api/auth', authRoutes);
app.use('/api/jobs', jobRoutes);
app.use('/api/users', userRoutes);

// Mount webhook route with raw body parsing to allow signature verification
app.use('/api/webhooks', express.raw({ type: '*/*' }), (req, res, next) => {
  // attach raw body for downstream handlers
  req.rawBody = req.body;
  next();
}, webhookRoutes);

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', service: 'backend-api' });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error('Unhandled Error:', err && err.stack ? err.stack : err);

  // Multer file size limit
  if (err && (err.code === 'LIMIT_FILE_SIZE' || err.message && err.message.includes('File too large'))) {
    return res.status(413).json({ error: 'Uploaded file is too large. Max size is 5MB.' });
  }

  // Multer invalid file type or our fileFilter errors
  if (err && err.message && err.message.toLowerCase().includes('invalid file type')) {
    return res.status(400).json({ error: err.message });
  }

  // Generic multer error
  if (err && err.name === 'MulterError') {
    return res.status(400).json({ error: err.message || 'File upload error' });
  }

  res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, () => {
  console.log(`Backend API running on port ${PORT}`);
});
