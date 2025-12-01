const express = require('express');
const router = express.Router();
const axios = require('axios');
const Conversation = require('../models/Conversation');
const PreferenceSummary = require('../models/PreferenceSummary');
const { protect } = require('../middleware/authMiddleware');

// RAG service configuration
const RAG_SERVICE_URL = process.env.RAG_SERVICE_URL || 'http://127.0.0.1:8001';

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

// POST /api/conversations/save - Save a new conversation with background preference summarization
router.post('/save', protect, async (req, res) => {
  try {
    // Step 1: Save the conversation first
    const conversation = new Conversation({
      user: req.user._id,
      selectedTopics: req.body.selectedTopics,
      topicConversations: req.body.topicConversations,
      allMessages: req.body.allMessages,
      timestamp: req.body.timestamp
    });

    const newConversation = await conversation.save();
    console.log(`Conversation saved with ID: ${newConversation._id}`);

    // Step 2: Immediately respond to frontend so user can continue
    res.status(201).json({
      conversation: newConversation,
      message: 'Conversation saved successfully. Preference summary is being generated in the background.'
    });

    // Step 3: Generate preference summary in the background (don't await)
    // This runs asynchronously and won't block the response
    (async () => {
      try {
        console.log('Starting background preference summarization...');

        const ragResponse = await axios.post(`${RAG_SERVICE_URL}/summarize-preferences`, {
          allMessages: req.body.allMessages,
          selectedTopics: req.body.selectedTopics,
          topicConversations: req.body.topicConversations,
          timestamp: req.body.timestamp,
          _id: newConversation._id.toString()
        }, {
          timeout: 120000, // 2 minute timeout for background process
          headers: {
            'Content-Type': 'application/json'
          }
        });

        if (ragResponse.data.success && ragResponse.data.summary) {
          console.log('Preference summary generated successfully');

          // Save the preference summary to MongoDB
          const summaryData = ragResponse.data.summary;
          const preferenceSummary = new PreferenceSummary({
            user: req.user._id,
            conversation: newConversation._id,
            color_and_contrast: summaryData.color_and_contrast,
            familiarity_and_identity: summaryData.familiarity_and_identity,
            overall_summary: summaryData.overall_summary,
            metadata: summaryData.metadata
          });

          await preferenceSummary.save();
          console.log(`Preference summary saved with ID: ${preferenceSummary._id}`);

          // Update conversation with reference to preference summary
          newConversation.preferenceSummary = preferenceSummary._id;
          await newConversation.save();
          console.log('Conversation updated with preference summary reference');
        } else {
          console.warn('RAG service returned unsuccessful response:', ragResponse.data);
        }
      } catch (ragError) {
        console.error('Background error in preference summarization:', ragError.message);
        // Log but don't fail - the conversation is already saved
      }
    })();

  } catch (err) {
    console.error('Error saving conversation:', err);
    res.status(400).json({ message: 'Failed to save conversation', error: err.message });
  }
});

module.exports = router;
