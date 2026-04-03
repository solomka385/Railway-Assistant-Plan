// routes/proxy.js
const express = require('express');
const router = express.Router();
const requireAuth = require('../middleware/auth');
const proxyController = require('../controllers/proxyController');

router.use(requireAuth);

router.post('/:chatId/process-message', proxyController.processMessage);
router.post('/:chatId/process-message-stream', proxyController.processMessageStream);

module.exports = router;