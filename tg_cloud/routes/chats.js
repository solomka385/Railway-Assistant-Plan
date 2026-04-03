// routes/chats.js
const express = require('express');
const router = express.Router();
const chatController = require('../controllers/chatController');
const requireAuth = require('../middleware/auth');

router.use(requireAuth); // все маршруты ниже требуют аутентификации

router.get('/', chatController.getChats);
router.post('/', chatController.createChat);
router.delete('/:id', chatController.deleteChat);
router.get('/:chatId/messages', chatController.getMessages);
router.post('/:chatId/messages', chatController.saveMessage);

module.exports = router;