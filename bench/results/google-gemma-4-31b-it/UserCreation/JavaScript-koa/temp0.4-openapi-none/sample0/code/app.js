const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS invitations (
    invite_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    used INTEGER DEFAULT 0
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
  )`);
});

// Helper to wrap db.get/run in promises
const dbGet = (sql, params = []) => new Promise((res, rej) => {
  db.get(sql, params, (err, row) => err ? rej(err) : res(row));
});
const dbRun = (sql, params = []) => new Promise((res, rej) => {
  db.run(sql, params, function(err) { err ? rej(err) : res(this); });
});

// POST /invite_user
router.post('/invite_user', async (ctx) => {
  const { email } = ctx.request.body;
  if (!email) {
    ctx.throw(400, 'Email is required');
  }

  try {
    const existing = await dbGet('SELECT invite_id FROM invitations WHERE email = ?', [email]);
    if (existing) {
      ctx.body = {
        invite_id: existing.invite_id,
        message: 'Invitation already exists for this email.'
      };
      return;
    }

    const invite_id = uuidv4();
    await dbRun('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', [invite_id, email]);
    
    ctx.body = {
      invite_id: invite_id,
      message: 'Invitation created successfully.'
    };
  } catch (err) {
    ctx.throw(500, err.message);
  }
});

// POST /create_user
router.post('/create_user', async (ctx) => {
  const { invite_id, user_name, password } = ctx.request.body;

  if (!invite_id || !user_name || !password) {
    ctx.throw(400, 'Missing required fields: invite_id, user_name, and password are required');
  }

  try {
    // 1. Validate invitation
    const invite = await dbGet('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id]);
    if (!invite) {
      ctx.status = 401;
      ctx.body = { message: 'Invalid invite_id' };
      return;
    }

    // 2. Check if username exists
    const userExists = await dbGet('SELECT id FROM users WHERE user_name = ?', [user_name]);
    if (userExists) {
      ctx.status = 400;
      ctx.body = { message: 'Username already exists. Try providing different username.' };
      return;
    }

    // 3. Hash password and create user
    const hashedPassword = await bcrypt.hash(password, 10);
    const email = invite.email;

    await dbRun('BEGIN TRANSACTION');
    try {
      await dbRun('INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)', [user_name, email, hashedPassword]);
      await dbRun('UPDATE invitations SET used = 1 WHERE invite_id = ?', [invite_id]);
      await dbRun('COMMIT');
    } catch (e) {
      await dbRun('ROLLBACK');
      throw e;
    }

    ctx.body = { message: 'User created successfully' };
  } catch (err) {
    if (err.message.includes('UNIQUE constraint failed')) {
      ctx.status = 400;
      ctx.body = { message: 'Username or Email already exists.' };
    } else {
      ctx.throw(500, err.message);
    }
  }
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});