const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const sqlite3 = require('sqlite3').verbose();
const dotenv = require('dotenv');

dotenv.config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key';
const PORT = 5000;
const HOST = '0.0.0.0';

const app = new Koa();
const router = new Router();

// Database Initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS secrets (
    username TEXT PRIMARY KEY,
    secret_value TEXT,
    FOREIGN KEY(username) REFERENCES users(username)
  )`);
});

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

// POST /register
router.post('/register', async (ctx) => {
  const { email, username, password } = ctx.request.body;

  if (!email || !username || !password) {
    ctx.status = 400;
    ctx.body = { message: 'Email, username, and password are required' };
    return;
  }

  const hashedPassword = await bcrypt.hash(password, 10);

  const query = `INSERT INTO users (username, email, password) VALUES (?, ?, ?)`;
  db.run(query, [username, email, hashedPassword], function(err) {
    if (err) {
      ctx.status = 400;
      ctx.body = { message: 'Email already in use or invalid data' };
    } else {
      ctx.status = 201;
      ctx.body = { message: 'Registration successful' };
    }
  });
});

// POST /login
router.post('/login', async (ctx) => {
  const { email, password } = ctx.request.body;

  if (!email || !password) {
    ctx.status = 401;
    ctx.body = { message: 'Invalid email or password' };
    return;
  }

  const query = `SELECT username, password FROM users WHERE email = ?`;
  db.get(query, [email], async (err, user) => {
    if (err || !user) {
      ctx.status = 401;
      ctx.body = { message: 'Invalid email or password' };
      return;
    }

    const match = await bcrypt.compare(password, user.password);
    if (match) {
      const token = jwt.sign({ username: user.username }, APP_SECRET, { expiresIn: '24h' });
      ctx.status = 200;
      ctx.body = { token, message: 'Login successful' };
    } else {
      ctx.status = 401;
      ctx.body = { message: 'Invalid email or password' };
    }
  });
});

// POST /set_secret
router.post('/set_secret', authMiddleware, async (ctx) => {
  const { username, secret } = ctx.request.body;

  if (!username || secret === undefined) {
    ctx.status = 400;
    ctx.body = { message: 'Username and secret are required' };
    return;
  }

  // Ensure the user is setting a secret for their own account
  if (ctx.state.user.username !== username) {
    ctx.status = 401;
    ctx.body = { message: 'Unauthorized to set secret for this user' };
    return;
  }

  const query = `INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)`;
  db.run(query, [username, secret], function(err) {
    if (err) {
      ctx.status = 500;
      ctx.body = { message: 'Database error' };
    } else {
      ctx.status = 200;
      ctx.body = { message: 'Secret has been set successfully' };
    }
  });
});

// GET /get_secret
router.get('/get_secret', authMiddleware, async (ctx) => {
  const { username } = ctx.query;

  if (!username) {
    ctx.status = 400;
    ctx.body = { message: 'Username query parameter is required' };
    return;
  }

  // Ensure the user is retrieving their own secret
  if (ctx.state.user.username !== username) {
    ctx.status = 401;
    ctx.body = { message: 'Invalid authentication token' };
    return;
  }

  const query = `SELECT secret_value FROM secrets WHERE username = ?`;
  db.get(query, [username], (err, row) => {
    if (err) {
      ctx.status = 500;
      ctx.body = { message: 'Database error' };
    } else if (row) {
      ctx.status = 200;
      ctx.body = { secret: row.secret_value };
    } else {
      ctx.status = 404;
      ctx.body = { message: 'Secret not found' };
    }
  });
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});