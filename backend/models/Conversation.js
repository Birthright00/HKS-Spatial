const mongoose = require('mongoose');

// A flexible schema for individual messages
const messageSchema = new mongoose.Schema({
  id: String,
  text: String,
  isUser: Boolean,
  timestamp: Date,
  type: String,
  questionnaire: mongoose.Schema.Types.Mixed,
}, { _id: false });

const conversationSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'User'
  },
  selectedTopics: [String],
  topicConversations: mongoose.Schema.Types.Mixed,
  allMessages: [messageSchema],
  preferenceSummary: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'PreferenceSummary'
  },
  timestamp: {
    type: Date,
    default: Date.now
  }
});

module.exports = mongoose.model('Conversation', conversationSchema);
