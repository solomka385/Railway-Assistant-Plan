// app.js
const express = require('express');
const cors = require('cors');
const path = require('path');
const config = require('./config');

const app = express();

// CORS
app.use(cors({
    origin: function (origin, callback) {
        if (!origin || config.allowedOrigins.includes(origin)) {
            callback(null, true);
        } else {
            callback(new Error('Not allowed by CORS'));
        }
    },
    credentials: true
}));

app.use(express.json());

// Статические файлы (из папки public)
app.use(express.static(path.join(__dirname, 'public')));

// Маршруты будут добавлены позже в server.js
// (чтобы сессия применялась до них)

module.exports = app;