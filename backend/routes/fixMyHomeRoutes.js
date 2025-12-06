const express = require('express');
const router = express.Router();
const FixMyHomeHistory = require('../models/FixMyHomeHistory');
const { protect } = require('../middleware/authMiddleware');

/**
 * POST /api/fix-my-home/save-result
 *
 * Save a Fix My Home generation result to history
 * Body should contain:
 * - selectedIssues: string[]
 * - comments: string
 * - noChangeComments: string
 * - originalImage: string (base64 data URL or path)
 * - transformedImage: string (base64 data URL or path, nullable)
 * - analysisText: string
 * - analysisJson: object (issues array and other analysis data)
 * - success: boolean
 * - error: string (optional)
 */
router.post('/save-result', protect, async (req, res) => {
  try {
    console.log('[Fix My Home] Saving result for user:', req.user._id);

    const {
      selectedIssues,
      comments,
      noChangeComments,
      originalImage,
      transformedImage,
      analysisText,
      analysisJson,
      success,
      error
    } = req.body;

    // Validate required fields
    if (!selectedIssues || !Array.isArray(selectedIssues)) {
      return res.status(400).json({
        message: 'selectedIssues is required and must be an array'
      });
    }

    if (!originalImage) {
      return res.status(400).json({
        message: 'originalImage is required'
      });
    }

    if (!analysisText) {
      return res.status(400).json({
        message: 'analysisText is required'
      });
    }

    if (!analysisJson) {
      return res.status(400).json({
        message: 'analysisJson is required'
      });
    }

    // Create new history entry
    const historyEntry = new FixMyHomeHistory({
      user: req.user._id,
      selectedIssues,
      comments: comments || '',
      noChangeComments: noChangeComments || '',
      originalImage,
      transformedImage: transformedImage || null,
      analysisText,
      analysisJson,
      success: success !== undefined ? success : true,
      error: error || null,
    });

    await historyEntry.save();

    console.log('[Fix My Home] Result saved successfully:', historyEntry._id);

    return res.status(201).json({
      message: 'Fix My Home result saved successfully',
      historyId: historyEntry._id,
      createdAt: historyEntry.createdAt,
    });

  } catch (error) {
    console.error('[Fix My Home] Error saving result:', error);
    return res.status(500).json({
      message: 'Failed to save Fix My Home result',
      error: error.message,
    });
  }
});

/**
 * GET /api/fix-my-home/history
 *
 * Retrieve all Fix My Home history entries for the authenticated user
 * Query params:
 * - limit: number (default: 50)
 * - offset: number (default: 0)
 * - sort: 'asc' | 'desc' (default: 'desc' - newest first)
 */
router.get('/history', protect, async (req, res) => {
  try {
    console.log('[Fix My Home] Fetching history for user:', req.user._id);

    const limit = parseInt(req.query.limit) || 50;
    const offset = parseInt(req.query.offset) || 0;
    const sort = req.query.sort === 'asc' ? 1 : -1;

    // Validate pagination params
    if (limit < 1 || limit > 100) {
      return res.status(400).json({
        message: 'limit must be between 1 and 100'
      });
    }

    if (offset < 0) {
      return res.status(400).json({
        message: 'offset must be non-negative'
      });
    }

    // Fetch history entries
    const historyEntries = await FixMyHomeHistory
      .find({ user: req.user._id })
      .sort({ createdAt: sort })
      .skip(offset)
      .limit(limit)
      .lean(); // Use lean() for better performance (returns plain JS objects)

    // Get total count for pagination
    const totalCount = await FixMyHomeHistory.countDocuments({ user: req.user._id });

    console.log(`[Fix My Home] Found ${historyEntries.length} entries (total: ${totalCount})`);

    return res.json({
      success: true,
      entries: historyEntries,
      pagination: {
        total: totalCount,
        limit,
        offset,
        hasMore: offset + historyEntries.length < totalCount,
      },
    });

  } catch (error) {
    console.error('[Fix My Home] Error fetching history:', error);
    return res.status(500).json({
      message: 'Failed to fetch Fix My Home history',
      error: error.message,
    });
  }
});

/**
 * GET /api/fix-my-home/history/:id
 *
 * Retrieve a specific Fix My Home history entry by ID
 */
router.get('/history/:id', protect, async (req, res) => {
  try {
    const { id } = req.params;

    console.log('[Fix My Home] Fetching history entry:', id);

    const historyEntry = await FixMyHomeHistory.findById(id).lean();

    if (!historyEntry) {
      return res.status(404).json({
        message: 'History entry not found'
      });
    }

    // Verify user owns this entry
    if (historyEntry.user.toString() !== req.user._id.toString()) {
      return res.status(403).json({
        message: 'Access denied: This entry belongs to another user'
      });
    }

    console.log('[Fix My Home] History entry found:', id);

    return res.json({
      success: true,
      entry: historyEntry,
    });

  } catch (error) {
    console.error('[Fix My Home] Error fetching history entry:', error);

    // Handle invalid ObjectId format
    if (error.name === 'CastError') {
      return res.status(400).json({
        message: 'Invalid history entry ID format',
      });
    }

    return res.status(500).json({
      message: 'Failed to fetch history entry',
      error: error.message,
    });
  }
});

/**
 * DELETE /api/fix-my-home/history/:id
 *
 * Delete a specific Fix My Home history entry
 */
router.delete('/history/:id', protect, async (req, res) => {
  try {
    const { id } = req.params;

    console.log('[Fix My Home] Deleting history entry:', id);

    const historyEntry = await FixMyHomeHistory.findById(id);

    if (!historyEntry) {
      return res.status(404).json({
        message: 'History entry not found'
      });
    }

    // Verify user owns this entry
    if (historyEntry.user.toString() !== req.user._id.toString()) {
      return res.status(403).json({
        message: 'Access denied: This entry belongs to another user'
      });
    }

    await historyEntry.deleteOne();

    console.log('[Fix My Home] History entry deleted:', id);

    return res.json({
      success: true,
      message: 'History entry deleted successfully',
    });

  } catch (error) {
    console.error('[Fix My Home] Error deleting history entry:', error);

    // Handle invalid ObjectId format
    if (error.name === 'CastError') {
      return res.status(400).json({
        message: 'Invalid history entry ID format',
      });
    }

    return res.status(500).json({
      message: 'Failed to delete history entry',
      error: error.message,
    });
  }
});

module.exports = router;
