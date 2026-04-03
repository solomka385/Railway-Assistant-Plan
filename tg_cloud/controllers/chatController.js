// controllers/chatController.js
const { getPool } = require('../db/pool');

exports.getChats = async (req, res) => {
  try {
    const pool = getPool();
    const result = await pool.query(
      'SELECT * FROM chats WHERE user_id = $1 ORDER BY created_at DESC',
      [req.session.userId]
    );
    res.json(result.rows);
  } catch (error) {
    console.error('Error fetching chats:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

exports.createChat = async (req, res) => {
  try {
    const { title } = req.body;
    const chatId = Date.now().toString();
    const pool = getPool();
    const result = await pool.query(
      'INSERT INTO chats (id, title, user_id) VALUES ($1, $2, $3) RETURNING *',
      [chatId, title || `Чат ${chatId}`, req.session.userId]
    );
    res.status(201).json(result.rows[0]);
  } catch (error) {
    console.error('Error creating chat:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

exports.deleteChat = async (req, res) => {
  try {
    const { id } = req.params;
    const pool = getPool();
    await pool.query('DELETE FROM messages WHERE chat_id = $1', [id]);
    const result = await pool.query(
      'DELETE FROM chats WHERE id = $1 AND user_id = $2',
      [id, req.session.userId]
    );
    if (result.rowCount === 0) return res.status(404).json({ error: 'Chat not found' });
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting chat:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

exports.getMessages = async (req, res) => {
  try {
    const { chatId } = req.params;
    const pool = getPool();
    const chatCheck = await pool.query(
      'SELECT id FROM chats WHERE id = $1 AND user_id = $2',
      [chatId, req.session.userId]
    );
    if (chatCheck.rows.length === 0) return res.status(404).json({ error: 'Chat not found' });

    const result = await pool.query(
      'SELECT * FROM messages WHERE chat_id = $1 ORDER BY timestamp ASC',
      [chatId]
    );
    res.json(result.rows);
  } catch (error) {
    console.error('Error fetching messages:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

exports.saveMessage = async (req, res) => {
  try {
    const { chatId } = req.params;
    const { type, text, mode = 'plan', sources = [], employees = [] } = req.body;
    
    const pool = getPool();
    const chatCheck = await pool.query(
      'SELECT id FROM chats WHERE id = $1 AND user_id = $2',
      [chatId, req.session.userId]
    );
    if (chatCheck.rows.length === 0) return res.status(404).json({ error: 'Chat not found' });

    const result = await pool.query(
      'INSERT INTO messages (chat_id, type, text, mode, sources, employees) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *',
      [chatId, type, text, mode, JSON.stringify(sources), JSON.stringify(employees)]
    );
    res.status(201).json(result.rows[0]);
  } catch (error) {
    console.error('Error saving message:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};