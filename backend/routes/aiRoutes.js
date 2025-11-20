const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');

const SYSTEM_PROMPT = `You are helping a caregiver uncover meaningful personal memories from an Alzheimer's patient to support reminiscence therapy and personalized home design.
"Was there a dish she made just for you?"

"Do you remember what the plates or table looked like?"`;

router.post('/generate-question', protect, async (req, res) => {
  const { topic, context, isSecondFollowUp } = req.body;
  const apiKey = process.env.OPENROUTER_API_KEY;

  try {
    const response = await fetch('https://api.openrouter.ai/v1/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'openrouter/ai/anthropic/claude-3-sonnet',
        prompt: SYSTEM_PROMPT,
        max_tokens: 100,
        temperature: 0.5,
        context: context,
        isSecondFollowUp: isSecondFollowUp,
        topic: topic,
      }),
    });

    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('Error generating question:', error);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;