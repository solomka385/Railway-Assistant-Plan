// controllers/knowledgeController.js
const { getPool } = require('../db/pool');

exports.getKnowledge = async (req, res) => {
  try {
    const pool = getPool();
    const result = await pool.query('SELECT * FROM knowledge_base ORDER BY created_at DESC');
    res.json(result.rows);
  } catch (error) {
    console.error('Error fetching knowledge base:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

exports.addKnowledge = async (req, res) => {
  try {
    const { question, answer } = req.body;
    if (!question || !answer) {
      return res.status(400).json({ error: 'Question and answer are required' });
    }
    const pool = getPool();
    const result = await pool.query(
      'INSERT INTO knowledge_base (question, answer) VALUES ($1, $2) RETURNING *',
      [question, answer]
    );
    res.status(201).json(result.rows[0]);
  } catch (error) {
    console.error('Error saving to knowledge base:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};