// controllers/proxyController.js
const ragService = require('../services/ragService');

exports.processMessage = async (req, res) => {
  try {
    const { question, session_id, mode = 'plan' } = req.body;
    if (!question?.trim()) {
      return res.status(400).json({ error: 'Question is required' });
    }
    const data = await ragService.sendQuestion(question, session_id, mode);
    res.json(data);
  } catch (error) {
    console.error('[processMessage] Error:', error);
    res.status(500).json({ error: 'RAG service error', message: error.message });
  }
};

exports.processMessageStream = async (req, res) => {
  try {
    const { question, session_id, mode = 'plan' } = req.body;
    if (!question?.trim()) {
      return res.status(400).json({ error: 'Question is required' });
    }

    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    });

    const response = await ragService.streamQuestion(question, session_id, mode);
    response.data.on('data', chunk => res.write(chunk));
    response.data.on('end', () => res.end());
    response.data.on('error', error => {
      console.error('Stream error:', error);
      res.write(`data: ${JSON.stringify({ type: 'error', chunk: 'Ошибка потока данных' })}\n\n`);
      res.end();
    });
  } catch (error) {
    console.error('[processMessageStream] Error:', error);
    res.write(`data: ${JSON.stringify({ type: 'error', chunk: error.message })}\n\n`);
    res.end();
  }
};