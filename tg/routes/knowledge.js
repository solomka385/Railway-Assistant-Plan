// routes/knowledge.js
const express = require('express');
const router = express.Router();
const requireAuth = require('../middleware/auth');
const knowledgeController = require('../controllers/knowledgeController');

router.use(requireAuth);

router.get('/', knowledgeController.getKnowledge);
router.post('/', knowledgeController.addKnowledge);

module.exports = router;