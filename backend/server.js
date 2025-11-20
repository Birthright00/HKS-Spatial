const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const dotenv = require('dotenv');
const path = require('path');
const { notFound, errorHandler } = require('./middleware/errorMiddleware');

// Load environment variables from .env file
dotenv.config();

const app = express();

// Environment variables
const PORT = process.env.PORT || 8000;
const HOST = process.env.HOST || '0.0.0.0';
const MONGODB_URI = process.env.MONGODB_URI;
const CORS_ORIGINS = process.env.CORS_ORIGINS ? process.env.CORS_ORIGINS.split(',') : [];

// CORS configuration
const corsOptions = {
  origin: (origin, callback) => {
    // Allow requests with no origin (like mobile apps or curl requests)
    if (!origin) return callback(null, true);
    if (CORS_ORIGINS.indexOf(origin) === -1) {
      const msg = 'The CORS policy for this site does not allow access from the specified Origin.';
      return callback(new Error(msg), false);
    }
    return callback(null, true);
  },
  optionsSuccessStatus: 200,
};
app.use(cors(corsOptions));

// Middleware for parsing JSON bodies
app.use(express.json());

// Connect to MongoDB
mongoose.connect(MONGODB_URI)
  .then(() => console.log('Successfully connected to MongoDB.'))
  .catch(err => console.error('MongoDB connection error:', err));

// Add more detailed connection listeners
const db = mongoose.connection;
db.on('error', console.error.bind(console, 'Mongoose connection error:'));
db.on('disconnected', () => console.log('Mongoose disconnected.'));

// Basic route for testing
app.get('/', (req, res) => {
  res.send('Welcome to the Spatial Design Studio API!');
});

// --- API HEALTH CHECK ---
// Add this new route to easily check DB connection status
app.get('/api/health', (req, res) => {
  const dbState = mongoose.connection.readyState;
  let status = 500;
  let message = 'Database not connected';

  if (dbState === 1) {
    status = 200;
    message = 'Database connection is healthy';
  }
  
  res.status(status).json({ 
    server: 'Running', 
    database: {
      status: message,
      readyState: dbState // 0: disconnected, 1: connected, 2: connecting, 3: disconnecting
    }
  });
});

// --- API ROUTES FOR YOUR FRONTEND ---
// This section tells Express how to handle incoming API requests.
// Each 'app.use' line delegates requests starting with a specific path
// to a dedicated router file, which contains the logic for saving and retrieving data.

// Handles user login and creation (saving new users to the database).
const authRoutes = require('./routes/authRoutes');
app.use('/api/auth', authRoutes);

const projectRoutes = require('./routes/projectRoutes');
app.use('/api/projects', projectRoutes);

const designRoutes = require('./routes/designRoutes');
app.use('/api/designs', designRoutes);

// Handles the Memory Bot's data (saving conversations to the database).
const conversationRoutes = require('./routes/conversationRoutes');
app.use('/api/conversations', conversationRoutes);

// --- SERVE FRONTEND ---
// This section serves the static files from the React/Vue/Svelte build folder
const frontendBuildPath = path.join(__dirname, '..', 'Spatial-Design-Studio-Frontend', 'frontend', 'dist');
app.use(express.static(frontendBuildPath));

// For any request that doesn't match one above, send back index.html
// This is for Single Page Application (SPA) routing
app.get('*', (req, res) => {
  res.sendFile(path.join(frontendBuildPath, 'index.html'));
});

// --- ERROR HANDLING MIDDLEWARE ---
// These must be placed after all other routes.
app.use(notFound);
app.use(errorHandler);

// Start the server
app.listen(PORT, HOST, () => {
  console.log(`Server is running on http://${HOST}:${PORT}`);
});
