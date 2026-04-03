// server.js
const app = require('./app');
const { initPools } = require('./db/pool');
const session = require('express-session');
const pgSession = require('connect-pg-simple')(session);
const config = require('./config');
const routes = require('./routes'); // импортируем маршруты
const path = require('path');
const port = 3000;

async function startServer() {
    try {
        const { sessionPool } = await initPools();

        // Настройка сессий
        const sessionConfig = {
            store: new pgSession({
                pool: sessionPool,
                tableName: 'user_sessions',
                createTableIfMissing: false,
            }),
            secret: config.session.secret,
            resave: false,
            saveUninitialized: false,
            cookie: {
                maxAge: config.session.maxAge,
                httpOnly: true,
                secure: false, // если HTTPS, то true
                sameSite: 'lax'
            }
        };
        app.use(session(sessionConfig));

        // Подключаем маршруты ПОСЛЕ сессии
        app.use('/api', routes);

        // SPA fallback — должно быть после маршрутов, но до listen
        app.get('*', (req, res) => {
            res.sendFile(path.join(__dirname, 'public', 'index.html'));
        });

        app.listen(port, '0.0.0.0', () => {
            console.log(`✅ Server running on http://0.0.0.0:${port}`);
        });
    } catch (error) {
        console.error('❌ Failed to start server:', error);
        process.exit(1);
    }
}

startServer();