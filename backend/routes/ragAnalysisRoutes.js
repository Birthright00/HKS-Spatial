const express = require('express');
const router = express.Router();
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const Conversation = require('../models/Conversation');
const Assessment = require('../models/Assessment');
const { protect } = require('../middleware/authMiddleware');

const upload = multer({ storage: multer.memoryStorage() });

/**
 * POST /api/rag-analysis/analyze-with-context
 *
 * Analyze image with personalized context from user's conversation and assessment data
 * This endpoint:
 * 1. Fetches user's most recent conversation (from Memory Bot)
 * 2. Fetches user's most recent assessment (from Fix My Home)
 * 3. Sends image + context to RAG-Langchain service
 * 4. Returns personalized analysis
 */
router.post('/analyze-with-context', protect, upload.single('image'), async (req, res) => {
  try {
    console.log('[RAG Analysis] Starting personalized analysis for user:', req.user._id);

    if (!req.file) {
      return res.status(400).json({ message: 'No image file uploaded' });
    }

    // Fetch user's most recent conversation from MongoDB
    const conversation = await Conversation.findOne({ user: req.user._id })
      .sort({ timestamp: -1 })
      .limit(1);

    // Fetch user's most recent assessment from MongoDB
    const assessment = await Assessment.findOne({ user: req.user._id })
      .sort({ createdAt: -1 })
      .limit(1);

    console.log('[RAG Analysis] Found conversation:', conversation ? 'Yes' : 'No');
    console.log('[RAG Analysis] Found assessment:', assessment ? 'Yes' : 'No');

    // Prepare form data for RAG service
    const formData = new FormData();
    formData.append('file', req.file.buffer, {
      filename: req.file.originalname,
      contentType: req.file.mimetype
    });

    // Build user context object
    const userContext = {};

    // Add conversation data if available
    if (conversation) {
      userContext.conversation = {
        selectedTopics: conversation.selectedTopics,
        topicConversations: conversation.topicConversations
      };
      console.log('[RAG Analysis] Including conversation topics:', conversation.selectedTopics.join(', '));
    }

    // Add assessment data if available
    if (assessment) {
      userContext.assessment = {
        selectedIssues: assessment.selectedIssues,
        comments: assessment.comments,
        noChangeComments: assessment.noChangeComments
      };
      console.log('[RAG Analysis] Including assessment issues:', assessment.selectedIssues.join(', '));
    }

    // Add user context as JSON string if we have any data
    if (Object.keys(userContext).length > 0) {
      formData.append('user_context', JSON.stringify(userContext));
      console.log('[RAG Analysis] Sending personalized context to RAG service');
    } else {
      console.log('[RAG Analysis] No personalized context available, using generic analysis');
    }

    // Call RAG-Langchain service
    const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8001';
    console.log('[RAG Analysis] Calling RAG service at:', ragServiceUrl);

    const response = await axios.post(`${ragServiceUrl}/analyze`, formData, {
      headers: formData.getHeaders(),
      timeout: 120000, // 2 minutes
      maxContentLength: 100000000, // 100MB
      maxBodyLength: 100000000 // 100MB
    });

    console.log('[RAG Analysis] RAG service responded successfully');

    return res.json(response.data);

  } catch (error) {
    console.error('[RAG Analysis] Error:', error.message);
    if (error.response) {
      console.error('[RAG Analysis] RAG service error:', error.response.data);
    }
    return res.status(500).json({
      message: 'Failed to analyze image with personalized context',
      error: error.message,
      details: error.response?.data || null
    });
  }
});

/**
 * GET /api/rag-analysis/user-context
 *
 * Fetch user's current conversation and assessment context
 * Useful for debugging or previewing what context will be sent to RAG
 */
router.get('/user-context', protect, async (req, res) => {
  try {
    const conversation = await Conversation.findOne({ user: req.user._id })
      .sort({ timestamp: -1 })
      .limit(1);

    const assessment = await Assessment.findOne({ user: req.user._id })
      .sort({ createdAt: -1 })
      .limit(1);

    return res.json({
      conversation: conversation ? {
        selectedTopics: conversation.selectedTopics,
        topicConversations: conversation.topicConversations,
        timestamp: conversation.timestamp
      } : null,
      assessment: assessment ? {
        selectedIssues: assessment.selectedIssues,
        comments: assessment.comments,
        noChangeComments: assessment.noChangeComments,
        createdAt: assessment.createdAt
      } : null
    });
  } catch (error) {
    console.error('[RAG Analysis] Error fetching user context:', error);
    return res.status(500).json({
      message: 'Failed to fetch user context',
      error: error.message
    });
  }
});

module.exports = router;
