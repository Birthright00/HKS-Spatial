const mongoose = require('mongoose');

const projectSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    trim: true,
  },
  description: {
    type: String,
    required: false
  },
  user: {
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'User' // This creates a link to the User model. Each project belongs to a user.
  },
  // You can add more fields here as your project evolves
  // e.g., createdAt, updatedAt timestamps
}, { timestamps: true });

module.exports = mongoose.model('Project', projectSchema);
