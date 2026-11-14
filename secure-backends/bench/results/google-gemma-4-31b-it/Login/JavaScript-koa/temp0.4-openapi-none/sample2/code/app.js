const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const app = new Koa();
const router = new Router();
const PORT = 5000;
const HOST = '0.0.0.0';
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_12345';

// Database Setup
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    password TEXT,
    name TEXT
  )`);
});

// Middleware
app.use(bodyParser());

// Routes
router.post('/register', async (ctx) => {
  const { email, password, name } = ctx.request.body;

  if (!email || !password || !name) {
    ctx.status = 400;
    ctx.body = { message: 'Email, password, and name are required' };
    return;
  }

  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    const userId = require('uuid').v4();

    const query = `INSERT INTO users (id, email, password, name) VALUES (?, ?, ?, ?)`;
    
    db.run(query, [userId, email, hashedPassword, name], function(err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          ctx.status = 400;
          ctx.body = { message: 'Email already in use or invalid data' };
        } else {
          ctx.status = 500;
          ctx.body = { message: 'Internal server error' };
        }
        return;
      }
      ctx.status = 201;
      ctx.body = { message: 'Registration successful' };
    });
  } catch (error) {
    ctx.status = 500;
    ctx.body = { message: 'Internal server error' };
  }
});

router.post('/login', async (ctx) => {
  const { email, password } = ctx.request.body;

  if (!email || !password) {
    ctx.status = 401;
    ctx.body = { message: 'Invalid email or password' };
    return;
  }

  const query = `SELECT * FROM users WHERE email = ?`;
  db.get(query, [email], async (err, user) => {
    if (err || !user) {
      ctx.status = 401;
      ctx.body = { message: 'Invalid email or password' };
      return;
    }

    const match = await bcrypt.compare(password, user.password);
    if (!match) {
      ctx.status = 401;
      ctx.body = { message: 'Invalid email or password' };
      return;
    }

    const token = jwt.sign({ id: user.id, email: user.email }, APP_SECRET, { expiresIn: '1h' });
    
    ctx.status = 200;
    ctx.body = {
      token: token,
      message: 'Login successful'
    };
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});