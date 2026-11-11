const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key';

// Database Setup
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

// Routes
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

router.post('/login', async (ctx) => {
  const { email, password } = ctx.request.body;

  if (!email || !password) {
    ctx.throw(400, 'Email and password are required');
  }

  db.get(`SELECT * FROM users WHERE email = ?`, [email], async (err, user) => {
    if (err || !user || !(await bcrypt.compare(password, user.password))) {
      ctx.status = 401;
      ctx.body = { message: 'Invalid email or password' };
      return;
    }

    const token = jwt.sign({ username: user.username, email: user.email }, APP_SECRET, { expiresIn: '24h' });
    ctx.status = 200;
    ctx.body = { token, message: 'Login successful' };
  });
});

router.post('/set_secret', authMiddleware, async (ctx) => {
  const { username, secret } = ctx.request.body;

  if (!username || secret === undefined) {
    ctx.throw(400, 'Username and secret are required');
  }

  // Ensure user is setting a secret for their own account
  if (ctx.state.user.username !== username) {
    ctx.throw(403, 'You can only set secrets for your own account');
  }

  const query = `INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)`;
  db.run(query, [username, secret], function(err) {
    if (err) {
      ctx.throw(500, 'Database error');
    }
    ctx.status = 200;
    ctx.body = { message: 'Secret has been set successfully' };
  });
});

router.get('/get_secret', authMiddleware, async (ctx) => {
  const { username } = ctx.request.query;

  if (!username) {
    ctx.throw(400, 'Username query parameter is required');
  }

  // Ensure user is retrieving their own secret
  if (ctx.state.user.username !== username) {
    ctx.throw(403, 'You can only retrieve your own secret');
  }

  db.get(`SELECT secret_value FROM secrets WHERE username = ?`, [username], (err, row) => {
    if (err) {
      ctx.throw(500, 'Database error');
    }
    if (!row) {
      ctx.status = 404;
      ctx.body = { message: 'Secret not found' };
      return;
    }
    ctx.status = 200;
    ctx.body = { secret: row.secret_value };
  });
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});