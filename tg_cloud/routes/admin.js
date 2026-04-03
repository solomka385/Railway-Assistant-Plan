// routes/admin.js
const express = require('express');
const router = express.Router();
const requireAuth = require('../middleware/auth');
const adminController = require('../controllers/adminController');

router.use(requireAuth);

router.post('/reindex', adminController.reindex);
router.get('/db-info', adminController.dbInfo);
router.get('/health', adminController.health);

module.exports = router;