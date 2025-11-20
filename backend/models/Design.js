const mongoose = require('mongoose');

const designSchema = new mongoose.Schema({
  name: {
    type: String,
    required: true,
    trim: true
  },
  description: {
    type: String
  },
  // This links the design to a project
  project: {
    // The 'type' specifies that we are storing a MongoDB Object ID.
    // Think of this as a unique ID or a "foreign key" from relational databases.
    type: mongoose.Schema.Types.ObjectId,
    // The 'ref' property is crucial. It tells Mongoose that the ObjectId stored
    // in this field refers to a document in the 'Project' collection/model.
    // This allows you to later use Mongoose's .populate() method to automatically
    // fetch the full project document when you query for a design.
    ref: 'Project', // This creates a link to the Project model. Each design belongs to a project.
    required: true
  },
  // You could store design data, like a JSON object from a canvas, here
  designData: {
    type: Object
  },
  user: {
    // Just like the 'project' field, this stores the unique ID of a user.
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    // This 'ref' points to the 'User' model. It establishes that every design
    // has an owner. This is essential for security, ensuring that when a user
    // requests their designs, you can filter and return only the ones they own.
    ref: 'User' // This links the design directly to a user for ownership and permissions.
  }
}, { timestamps: true });

module.exports = mongoose.model('Design', designSchema);
