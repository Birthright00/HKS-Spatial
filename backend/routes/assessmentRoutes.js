const express = require('express');
const router = express.Router();
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const Assessment = require('../models/Assessment');
const { protect } = require('../middleware/authMiddleware');

// Ensure uploads directory exists
const uploadsDir = path.join(__dirname, '..', 'uploads');
if (!fs.existsSync(uploadsDir)) {
  fs.mkdirSync(uploadsDir, { recursive: true });
}

// Multer disk storage configuration
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, uploadsDir),
  filename: (_req, file, cb) => {
    const unique = Date.now() + '-' + Math.round(Math.random() * 1e9);
    cb(null, `${file.fieldname}-${unique}${path.extname(file.originalname)}`);
  }
});
const upload = multer({ storage });

// POST /api/assessments
router.post('/', protect, upload.single('image'), async (req, res) => {
  console.log('Processing POST /api/assessments request...');

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
      } catch { /* ignore malformed JSON */ }
    }

    const doc = new Assessment({
      user: req.user._id,
      selectedIssues: parsedIssues,
      comments: req.body.comments || '',
      noChangeComments: req.body.noChangeComments || '',
      imagePath: `/uploads/${req.file.filename}`,
    });

    const saved = await doc.save();
    console.log('Assessment saved successfully:', saved._id);
    return res.status(201).json(saved);
  } catch (err) {
    console.error('Assessment upload error:', err);
    return res.status(500).json({ message: 'Failed to save assessment' });
  }
});

module.exports = router;
