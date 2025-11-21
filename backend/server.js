const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const Assessment = require('./models/Assessment');
const { protect } = require('./middleware/authMiddleware');
const { notFound, errorHandler } = require('./middleware/errorMiddleware');

// Load environment variables from .env file
dotenv.config();

const app = express();

// Request Logger Middleware
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl}`);
  next();
});

// Environment variables
const PORT = process.env.PORT || 8000;
const HOST = process.env.HOST || '0.0.0.0';
const MONGODB_URI = process.env.MONGODB_URI;
const CORS_ORIGINS = process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : [];

// CORS configuration
const corsOptions = {
  origin: (origin, callback) => {
    if (!origin) return callback(null, true);
    // Allow any origin to support access via network IP
    return callback(null, true);
  },
  optionsSuccessStatus: 200,
};
app.use(cors(corsOptions));

// Middleware for parsing JSON bodies
app.use(express.json());

// Connect to MongoDB
mongoose.connect(MONGODB_URI, {
  family: 4, // Force IPv4
})
  .then(() => console.log('Successfully connected to MongoDB.'))
  .catch(err => console.error('MongoDB connection error:', err));

// --- CONFIGURE UPLOADS (INLINE) ---
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, uploadsDir),
  filename: (_req, file, cb) => {
    const unique = Date.now() + '-' + Math.round(Math.random() * 1e9);
    cb(null, `${file.fieldname}-${unique}${path.extname(file.originalname)}`);
  }
});
const upload = multer({ storage });

// --- API ROUTES ---

app.get('/', (req, res) => {
  res.send('Welcome to the Spatial Design Studio API!');
});

app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'ok', dbState: mongoose.connection.readyState });
});

// Auth Routes
const authRoutes = require('./routes/authRoutes');
app.use('/api/auth', authRoutes);

// Project & Design Routes
const projectRoutes = require('./routes/projectRoutes');
app.use('/api/projects', projectRoutes);
const designRoutes = require('./routes/designRoutes');
app.use('/api/designs', designRoutes);

// Conversation Routes
const conversationRoutes = require('./routes/conversationRoutes');
app.use('/api/conversations', conversationRoutes);

// (FIXED) Inline Assessment Route - Guarantees the route exists
app.post('/api/assessments', protect, upload.single('image'), async (req, res) => {
  console.log('Processing POST /api/assessments (Inline Handler)...');
  try {
    if (!req.file) {
      console.log('Error: No file in request');
      return res.status(400).json({ message: 'No image file uploaded' });
    }

    let parsedIssues = [];
    if (req.body.selectedIssues) {
      try {
        const tmp = JSON.parse(req.body.selectedIssues);
        if (Array.isArray(tmp)) parsedIssues = tmp;
      } catch { /* ignore */ }
    }

    const doc = new Assessment({
      user: req.user._id,
      selectedIssues: parsedIssues,
      comments: req.body.comments || '',
      imagePath: `/uploads/${req.file.filename}`
    });

    const saved = await doc.save();
    console.log('Assessment saved successfully:', saved._id);
    return res.status(201).json(saved);
  } catch (err) {
    console.error('Assessment upload error:', err);
    return res.status(500).json({ message: 'Failed to save assessment' });
  }
});

// Serve uploaded images
app.use('/uploads', express.static(uploadsDir));

// --- SERVE FRONTEND ---
const frontendBuildPath = path.join(__dirname, '..', 'Spatial-Design-Studio-Frontend', 'frontend', 'dist');
app.use(express.static(frontendBuildPath));

app.get('*', (req, res) => {
  res.sendFile(path.join(frontendBuildPath, 'index.html'));
});

// Error Middleware
app.use(notFound);
app.use(errorHandler);

app.listen(PORT, HOST, () => {
  console.log(`Server is running on http://${HOST}:${PORT}`);
});
