// config/index.js
require('dotenv').config();
const fs = require('fs');

// Обработка PG_HOSTS: если переменная есть и не пустая, разбиваем и чистим
const pgHostsEnv = process.env.PG_HOSTS;
let pgHostsArray;
if (pgHostsEnv && pgHostsEnv.trim() !== '') {
    pgHostsArray = pgHostsEnv.split(',').map(h => h.trim()).filter(h => h);
} else {
    // Значение по умолчанию (один хост из старого списка)
    pgHostsArray = ['###'];
}

console.log('[CONFIG] PG_HOSTS from env:', process.env.PG_HOSTS);
console.log('[CONFIG] Final hosts array:', pgHostsArray);

// Путь к сертификату
const CERT_PATH = "/home/solomka385/.postgresql/root.crt";

module.exports = {
    db: {
        hosts: pgHostsArray,
        port: process.env.PG_PORT ||  ###,
        database: process.env.PG_DB || ###,
        user: process.env.PG_USER || ###,
        password: process.env.PG_PASSWORD || ###,
        ssl: {
            rejectUnauthorized: true,
            ca: fs.readFileSync(CERT_PATH).toString()
        },
        pool: {
            max: 10,
            idleTimeoutMillis: 30000,
        }
    },
    redis: {
        url: process.env.REDIS_URL || 'redis://:your_redis_password_123@localhost:6379'
    },
    session: {
        secret: process.env.SESSION_SECRET || 'your_strong_secret_key_change_me',
        maxAge: 30 * 24 * 60 * 60 * 1000 // 30 дней
    },
    ragApi: {
        baseUrl: process.env.RAG_API_BASE || 'https://###',
    },
    allowedOrigins: [
        'http://###',
        'https://###',
        'http://localhost:3000'
    ]
};