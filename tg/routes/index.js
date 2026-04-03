// routes/index.js
const express = require('express');
const authRoutes = require('./auth');
const chatsRoutes = require('./chats');
const proxyRoutes = require('./proxy');
const knowledgeRoutes = require('./knowledge');
const adminRoutes = require('./admin');
const martsRoutes = require('./marts');

const router = express.Router();

router.use(authRoutes); // без префикса, так как они уже /api/...
router.use('/chats', chatsRoutes); // будут /api/chats/...
router.use('/chats', proxyRoutes); // /api/chats/:id/process-message
router.use('/knowledge', knowledgeRoutes); // /api/knowledge
router.use(adminRoutes); // /api/reindex, /api/db-info, /health
router.use(martsRoutes); // /api/marts-data

module.exports = router;