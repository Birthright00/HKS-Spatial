const express = require('express');
const router = express.Router();
const Project = require('../models/Project');
const { protect } = require('../middleware/authMiddleware');

// GET /api/projects - Get all projects for the logged-in user
router.get('/', protect, async (req, res) => {
  try {
    const projects = await Project.find({ user: req.user._id });
    res.json(projects);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// GET /api/projects/:id - Get a single project
router.get('/:id', protect, getProject, (req, res) => {
  res.json(res.project);
});

// POST /api/projects - Create a new project
router.post('/', protect, async (req, res) => {
  const project = new Project({
    name: req.body.name,
    description: req.body.description,
    user: req.user._id,
  });

  try {
    const newProject = await project.save();
    res.status(201).json(newProject);
  } catch (err) {
    res.status(400).json({ message: err.message });
  }
});

// PATCH /api/projects/:id - Update a project
router.patch('/:id', protect, getProject, async (req, res) => {
  if (req.body.name != null) {
    res.project.name = req.body.name;
  }
  if (req.body.description != null) {
    res.project.description = req.body.description;
  }
  try {
    const updatedProject = await res.project.save();
    res.json(updatedProject);
  } catch (err) {
    res.status(400).json({ message: err.message });
  }
});

// DELETE /api/projects/:id - Delete a project
router.delete('/:id', protect, getProject, async (req, res) => {
  try {
    await res.project.deleteOne();
    res.json({ message: 'Deleted Project' });
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// Middleware function to get project by ID
async function getProject(req, res, next) {
  let project;
  try {
    project = await Project.findById(req.params.id);
    if (project == null) {
      return res.status(404).json({ message: 'Cannot find project' });
    }
    // Check if project belongs to user
    if (project.user.toString() !== req.user._id.toString()) {
        return res.status(401).json({ message: 'Not authorized' });
    }
  } catch (err) {
    return res.status(500).json({ message: err.message });
  }

  res.project = project;
  next();
}

module.exports = router;
