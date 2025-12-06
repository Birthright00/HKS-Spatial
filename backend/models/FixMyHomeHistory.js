const mongoose = require('mongoose');

/**
 * Schema for storing Fix My Home generation results
 * This stores the complete result of a Fix My Home session including:
 * - Original input image
 * - Generated/transformed image
 * - Analysis JSON with issues and recommendations
 * - User context (selected issues, comments)
 */
const fixMyHomeHistorySchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'User',
    index: true, // Index for efficient querying by user
  },
  // User input context
  selectedIssues: {
    type: [String],
    required: true,
  },
  comments: {
    type: String,
    default: '',
  },
  noChangeComments: {
    type: String,
    default: '',
  },
  // Images - stored as paths or base64 strings
  originalImage: {
    type: String, // Path to uploaded image or base64 data URL
    required: true,
  },
  transformedImage: {
    type: String, // Path to generated image or base64 data URL
    required: false, // May be null if transformation failed
  },
  // Analysis results
  analysisText: {
    type: String,
    required: true,
  },
  analysisJson: {
    type: mongoose.Schema.Types.Mixed, // Flexible JSON structure for issues
    required: true,
  },
  // Metadata
  success: {
    type: Boolean,
    default: true,
  },
  error: {
    type: String,
    default: null,
  },
}, {
  timestamps: true // Adds createdAt and updatedAt fields
});

// Index for sorting by creation time
fixMyHomeHistorySchema.index({ createdAt: -1 });

// Compound index for user + creation time queries
fixMyHomeHistorySchema.index({ user: 1, createdAt: -1 });

module.exports = mongoose.model('FixMyHomeHistory', fixMyHomeHistorySchema);
