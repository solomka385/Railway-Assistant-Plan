// db/pool.js
const { Pool } = require('pg');
const config = require('../config');

let pool;
let sessionPool;

async function findMasterHost() {
    console.log('[POOL] Starting master search with hosts:', config.db.hosts);
    const sslConfig = config.db.ssl;
    for (const host of config.db.hosts) {
        console.log(`[POOL] Testing host: ${host}`);
        const testPool = new Pool({
            host: host,
            port: config.db.port,
            database: config.db.database,
            user: config.db.user,
            password: config.db.password,
            ssl: sslConfig,
            connectionTimeoutMillis: 5000,
        });

        let client;
        try {
            client = await testPool.connect();
            const res = await client.query('SHOW transaction_read_only');
            const readOnly = res.rows[0].transaction_read_only === 'on';
            if (!readOnly) {
                console.log(`✅ Хост ${host} подходит (мастер)`);
                return host;
            } else {
                console.log(`❌ Хост ${host} в режиме read-only (реплика)`);
            }
        } catch (err) {
            console.log(`⚠️ Ошибка подключения к ${host}:`, err.message);
        } finally {
            if (client) client.release();
            await testPool.end();
        }
    }
    throw new Error('Не удалось найти мастер-хост PostgreSQL');
}

async function initPools() {
    console.log('[POOL] initPools started');
    const masterHost = await findMasterHost();
    console.log(`✅ Выбран мастер-хост: ${masterHost}`);

    const poolConfig = {
        host: masterHost,
        port: config.db.port,
        database: config.db.database,
        user: config.db.user,
        password: config.db.password,
        ssl: config.db.ssl,
        ...config.db.pool
    };

    pool = new Pool(poolConfig);
    sessionPool = new Pool({ ...poolConfig, max: 2 });

    // Устанавливаем search_path для пула
    pool.on('connect', (client) => {
        client.query('SET search_path TO rag_app,public');
    });
    sessionPool.on('connect', (client) => {
        client.query('SET search_path TO rag_app,public');
    });

    const client = await pool.connect();
    await client.query('SELECT 1');
    client.release();
    console.log('✅ PostgreSQL пулы инициализированы');

    await createTablesIfNotExists();

    return { pool, sessionPool };
}

async function createTablesIfNotExists() {
    const createSessionTableQuery = `
        CREATE TABLE IF NOT EXISTS user_sessions (
            "sid" varchar NOT NULL COLLATE "default" PRIMARY KEY,
            "sess" json NOT NULL,
            "expire" timestamp(6) NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_user_sessions_expire ON user_sessions ("expire");
    `;
    const createUsersTableQuery = `
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    `;
    const createChatsTableQuery = `
        CREATE TABLE IF NOT EXISTS chats (
            id VARCHAR(50) PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            user_id VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    `;
    const createMessagesTableQuery = `
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            chat_id VARCHAR(50) NOT NULL,
            type VARCHAR(10) NOT NULL,
            text TEXT NOT NULL,
            mode VARCHAR(10) DEFAULT 'plan',
            sources JSONB DEFAULT '[]'::jsonb,
            employees JSONB DEFAULT '[]'::jsonb,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    `;
    const createKnowledgeTableQuery = `
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id SERIAL PRIMARY KEY,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category VARCHAR(50),
            usage_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(question, category)
        );
    `;

    let client;
    try {
        client = await sessionPool.connect();
        await client.query(createSessionTableQuery);
        await client.query(createUsersTableQuery);
        await client.query(createChatsTableQuery);
        await client.query(createMessagesTableQuery);
        await client.query(createKnowledgeTableQuery);
        console.log('✅ Базовые таблицы проверены/созданы');
    } catch (err) {
        console.error('❌ Ошибка при создании таблиц:', err.message);
    } finally {
        if (client) client.release();
    }
}

function getPool() {
    if (!pool) throw new Error('Database pool not initialized');
    return pool;
}

function getSessionPool() {
    if (!sessionPool) throw new Error('Session pool not initialized');
    return sessionPool;
}

module.exports = { initPools, getPool, getSessionPool };