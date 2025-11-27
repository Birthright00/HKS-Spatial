const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');
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

// CORS configuration
app.use(cors({
  origin: (origin, cb) => {
    if (!origin) return cb(null, true);
    // Allow any origin to support access via network IP
    return cb(null, true);
  },
  optionsSuccessStatus: 200,
}));

// Middleware for parsing JSON bodies
app.use(express.json());

// Connect to MongoDB
mongoose.connect(MONGODB_URI, {
  family: 4, // Force IPv4
})
  .then(() => console.log('Successfully connected to MongoDB.'))
  .catch(err => console.error('MongoDB connection error:', err));

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

// Assessment Routes
const assessmentRoutes = require('./routes/assessmentRoutes');
app.use('/api/assessments', assessmentRoutes);

// RAG Analysis Routes
const ragAnalysisRoutes = require('./routes/ragAnalysisRoutes');
app.use('/api/rag-analysis', ragAnalysisRoutes);

// Static uploads
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}
app.use('/uploads', express.static(uploadsDir));

// --- FRONTEND ---
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
