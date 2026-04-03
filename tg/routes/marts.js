// routes/marts.js
const express = require('express');
const martsController = require('../controllers/martsController');
const requireAuth = require('../middleware/auth');

const router = express.Router();

// Получение данных из витрин по геометкам (требует авторизации)
router.post('/marts-data', requireAuth, martsController.getMartsData);

// Экспорт данных по станциям в Excel (требует авторизации)
router.post('/export-stations-excel', requireAuth, martsController.exportMartsDataToExcel);

module.exports = router;
