// controllers/adminController.js
const { getPool } = require('../db/pool');
const axios = require('axios');
const config = require('../config');

exports.reindex = async (req, res) => {
  try {
    console.log('[REINDEX] Starting reindex...');
    const response = await axios.post(`${config.ragApi.baseUrl}/reindex`, {}, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 300000
    });
    console.log('[REINDEX] Completed:', response.data);
    res.json({ status: 'success', message: response.data.message });
  } catch (error) {
    console.error('[REINDEX] Error:', error);
    res.status(500).json({ status: 'error', message: `Ошибка переиндексации: ${error.message}` });
  }
};

exports.dbInfo = async (req, res) => {
  try {
    const pool = getPool();
    const chatsInfo = await pool.query(
      `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'chats' ORDER BY ordinal_position`
    );
    const messagesInfo = await pool.query(
      `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'messages' ORDER BY ordinal_position`
    );
    res.json({ chats: chatsInfo.rows, messages: messagesInfo.rows });
  } catch (error) {
    console.error('Error getting DB info:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

exports.health = async (req, res) => {
  try {
    const pool = getPool();
    await pool.query('SELECT 1');
    // Здесь можно добавить проверку Redis, если используется
    res.json({ status: 'OK', postgres: 'connected', timestamp: new Date().toISOString() });
  } catch (error) {
    res.status(500).json({ status: 'ERROR', error: error.message, timestamp: new Date().toISOString() });
  }
};