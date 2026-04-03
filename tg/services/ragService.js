// services/ragService.js
const axios = require('axios');
const config = require('../config');

exports.sendQuestion = async (question, sessionId, mode) => {
  const url = `${config.ragApi.baseUrl}/ask`;
  const response = await axios.post(url, { question, session_id: sessionId, mode }, {
    timeout: 300000,
    headers: { 'Content-Type': 'application/json' }
  });
  return response.data;
};

exports.streamQuestion = async (question, sessionId, mode) => {
  const url = `${config.ragApi.baseUrl}/ask-stream`;
  return axios.post(url, { question, session_id: sessionId, mode }, {
    timeout: 300000,
    responseType: 'stream'
  });
};