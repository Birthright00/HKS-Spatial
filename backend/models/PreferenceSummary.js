const mongoose = require('mongoose');

// Schema for individual category preferences
const categoryPreferenceSchema = new mongoose.Schema({
  user_preferences: [String],
  guideline_considerations: [String],
  balanced_recommendations: [String],
  confidence_level: {
    type: String,
    enum: ['high', 'medium', 'low']
  }
}, { _id: false });

// Schema for metadata
const metadataSchema = new mongoose.Schema({
  timestamp: String,
  model: String,
  conversation_id: String,
  message_count: Number,
  rag_enabled: Boolean,
  vector_store: String
}, { _id: false });

// Main preference summary schema
const preferenceSummarySchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'User'
  },
  conversation: {
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'Conversation'
  },
  color_and_contrast: categoryPreferenceSchema,
  familiarity_and_identity: categoryPreferenceSchema,
  overall_summary: String,
  metadata: metadataSchema,
  createdAt: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('PreferenceSummary', preferenceSummarySchema);
