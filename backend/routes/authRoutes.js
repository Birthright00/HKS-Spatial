const express = require('express');
const router = express.Router();
const User = require('../models/User');
const jwt = require('jsonwebtoken');
const { protect } = require('../middleware/authMiddleware');

// Generate Token
const generateToken = (id) => {
  return jwt.sign({ id }, process.env.JWT_SECRET, {
    expiresIn: '30d',
  });
};

// @desc    Get user profile
// @route   GET /api/auth/me
router.get('/me', protect, async (req, res) => {
  // The `protect` middleware already fetched the user and attached it to `req.user`
  res.json({
    _id: req.user._id,
    name: req.user.name,
    username: req.user.username,
  });
});

// The /register route is no longer needed as this logic is merged into /login.

// @desc    Auth user & get token (or create user if they don't exist)
// @route   POST /api/auth/login
router.post('/login', async (req, res) => {
  const { username, password } = req.body;

  // Add validation to ensure a username is provided.
  if (!username || !password) {
    return res.status(400).json({ message: 'Please provide a username and password.' });
  }

  try {
    let user = await User.findOne({ username });

    if (user) {
      // User exists, so we check their password
      if (await user.matchPassword(password)) {
        res.json({
          _id: user._id,
          name: user.name,
          username: user.username,
          token: generateToken(user._id),
        });
      } else {
        // Password does not match
        return res.status(401).json({ message: 'Invalid password' });
      }
    } else {
      // User does not exist, so we create a new one
      const name = username;
      user = await User.create({ name, username, password });

      if (user) {
        res.status(201).json({
          _id: user._id,
          name: user.name,
          username: user.username,
          token: generateToken(user._id),
        });
      } else {
        return res.status(400).json({ message: 'Could not create user' });
      }
    }
  } catch (error) {
    console.error('Error during login/registration:', error);
    res.status(500).json({ message: error.message });
  }
});

module.exports = router;
