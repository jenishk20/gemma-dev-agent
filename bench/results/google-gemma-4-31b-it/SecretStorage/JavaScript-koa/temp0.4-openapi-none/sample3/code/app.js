const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const sqlite3 = require('sqlite3');
const { promisify } = require('util');

const app = new Koa();
const router = new Router();
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key';

// Database Setup
const db = new sqlite3.Database('db.sqlite3');
const dbRun = promisify(db.run.bind(db));
const dbGet = promisify(db.get.bind(db));

async function initDb() {
    await dbRun(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )`);
    await dbRun(`CREATE TABLE IF NOT EXISTS secrets (
        username TEXT PRIMARY KEY,
        secret_value TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    )`);
}

// Middleware for JWT Authentication
const authMiddleware = async (ctx, next) => {
    const authHeader = ctx.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        ctx.throw(401, 'Invalid authentication token');
    }
    const token = authHeader.split(' ')[1];
    try {
        const decoded = jwt.verify(token, APP_SECRET);
        ctx.state.user = decoded;
        await next();
    } catch (err) {
        ctx.throw(401, 'Invalid authentication token');
    }
};

// Routes
router.post('/register', async (ctx) => {
    const { email, username, password } = ctx.request.body;
    if (!email || !username || !password) {
        ctx.status = 400;
        ctx.body = { message: 'Email, username and password are required' };
        return;
    }

    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        await dbRun('INSERT INTO users (email, username, password) VALUES (?, ?, ?)', [email, username, hashedPassword]);
        ctx.status = 201;
        ctx.body = { message: 'Registration successful' };
    } catch (err) {
        ctx.status = 400;
        ctx.body = { message: 'Email already in use or invalid data' };
    }
});

router.post('/login', async (ctx) => {
    const { email, password } = ctx.request.body;
    if (!email || !password) {
        ctx.status = 401;
        ctx.body = { message: 'Invalid email or password' };
        return;
    }

    const user = await dbGet('SELECT * FROM users WHERE email = ?', [email]);
    if (!user || !(await bcrypt.compare(password, user.password))) {
        ctx.status = 401;
        ctx.body = { message: 'Invalid email or password' };
        return;
    }

    const token = jwt.sign({ username: user.username }, APP_SECRET, { expiresIn: '24h' });
    ctx.status = 200;
    ctx.body = { token, message: 'Login successful' };
});

router.post('/set_secret', authMiddleware, async (ctx) => {
    const { username, secret } = ctx.request.body;
    
    // Security check: Ensure the authenticated user is the one setting the secret
    if (ctx.state.user.username !== username) {
        ctx.status = 401;
        ctx.body = { message: 'Unauthorized: Username mismatch' };
        return;
    }

    await dbRun('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', [username, secret]);
    ctx.status = 200;
    ctx.body = { message: 'Secret has been set successfully' };
});

router.get('/get_secret', authMiddleware, async (ctx) => {
    const { username } = ctx.query;
    
    if (!username) {
        ctx.status = 400;
        ctx.body = { message: 'Username query parameter is required' };
        return;
    }

    // Security check: Ensure the authenticated user is the one requesting the secret
    if (ctx.state.user.username !== username) {
        ctx.status = 401;
        ctx.body = { message: 'Invalid authentication token' };
        return;
    }

    const row = await dbGet('SELECT secret_value FROM secrets WHERE username = ?', [username]);
    if (!row) {
        ctx.status = 404;
        ctx.body = { message: 'Secret not found' };
        return;
    }

    ctx.status = 200;
    ctx.body = { secret: row.secret_value };
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

initDb().then(() => {
    app.listen(5000, '0.0.0.0', () => {
        console.log('Server running on http://0.0.0.0:5000');
    });
}).catch(err => {
    console.error('Database initialization failed', err);
});