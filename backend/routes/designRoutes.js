const express = require('express');
const router = express.Router();
const Design = require('../models/Design');
const { protect } = require('../middleware/authMiddleware');

// GET all designs (optionally filter by project) for the logged-in user
router.get('/', protect, async (req, res) => {
  try {
    const filter = { user: req.user._id };
    if (req.query.projectId) {
        filter.project = req.query.projectId;
    }
    const designs = await Design.find(filter);
    res.json(designs);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
});

// POST a new design
router.post('/', protect, async (req, res) => {
  const design = new Design({
    name: req.body.name,
    description: req.body.description,
    project: req.body.project,
    designData: req.body.designData,
    user: req.user._id
  });

  try {
    const newDesign = await design.save();
    res.status(201).json(newDesign);
  } catch (err) {
    res.status(400).json({ message: err.message });
  }
});

// GET a single design
router.get('/:id', protect, getDesign, (req, res) => {
  res.json(res.design);
});

// PATCH update a design
router.patch('/:id', protect, getDesign, async (req, res) => {
    if (req.body.name != null) res.design.name = req.body.name;
    if (req.body.description != null) res.design.description = req.body.description;
    if (req.body.designData != null) res.design.designData = req.body.designData;
    try {
        const updatedDesign = await res.design.save();
        res.json(updatedDesign);
    } catch (err) {
        res.status(400).json({ message: err.message });
    }
});

// DELETE a design
router.delete('/:id', protect, getDesign, async (req, res) => {
    try {
        await res.design.deleteOne();
        res.json({ message: 'Deleted Design' });
    } catch (err) {
        res.status(500).json({ message: err.message });
    }
});

async function getDesign(req, res, next) {
    let design;
    try {
        design = await Design.findById(req.params.id);
        if (design == null) {
            return res.status(404).json({ message: 'Cannot find design' });
        }
        // Check if design belongs to user
        if (design.user.toString() !== req.user._id.toString()) {
            return res.status(401).json({ message: 'Not authorized' });
        }
    } catch (err) {
        return res.status(500).json({ message: err.message });
    }
    res.design = design;
    next();
}

module.exports = router;
