const express = require('express');
const router = express.Router();
const Conversation = require('../models/Conversation');
const { protect } = require('../middleware/authMiddleware');

// GET /api/conversations - Get all conversations for a user
router.get('/', protect, async (req, res) => {
    try {
        const conversations = await Conversation.find({ user: req.user._id }).sort({ timestamp: -1 });
        res.json(conversations);
    } catch (err) {
        console.error('Error fetching conversations:', err);
        res.status(500).json({ message: 'Failed to fetch conversations', error: err.message });
    }
});

// POST /api/conversations/save - Save a new conversation
router.post('/save', protect, async (req, res) => {
  const conversation = new Conversation({
    user: req.user._id,
    selectedTopics: req.body.selectedTopics,
    topicConversations: req.body.topicConversations,
    allMessages: req.body.allMessages,
    timestamp: req.body.timestamp
  });

  try {
    const newConversation = await conversation.save();
    res.status(201).json(newConversation);
  } catch (err) {
    console.error('Error saving conversation:', err);
    res.status(400).json({ message: 'Failed to save conversation', error: err.message });
  }
});

module.exports = router;
