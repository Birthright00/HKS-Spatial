const mongoose = require('mongoose');

const assessmentSchema = new mongoose.Schema({
  user: {
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'User',
  },
  selectedIssues: {
    type: [String],
    required: true,
  },
  comments: {
    type: String,
  },
  noChangeComments: {
    type: String,
  },
  imagePath: {
    type: String,
    required: true,
  },
}, { timestamps: true });

module.exports = mongoose.model('Assessment', assessmentSchema);
