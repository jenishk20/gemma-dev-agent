const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const bcrypt = require('bcrypt');
require('dotenv').config();

const app = new Koa();
const router = new Router();
const PORT = 5000;
const HOST = '0.0.0.0';

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS invitations (
    invite_id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    used INTEGER DEFAULT 0
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT UNIQUE,
    email TEXT UNIQUE,
    password TEXT
  )`);
});

// Helper to wrap db.get/run in promises
const dbGet = (query, params = []) => new Promise((resolve, reject) => {
  db.get(query, params, (err, row) => err ? reject(err) : resolve(row));
});

const dbRun = (query, params = []) => new Promise((resolve, reject) => {
  db.run(query, params, function(err) { err ? reject(err) : resolve(this); });
});

// POST /invite_user
router.post('/invite_user', async (ctx) => {
  const { email } = ctx.request.body;

  if (!email) {
    ctx.throw(400, 'Email is required');
  }

  try {
    // Check if invitation already exists for this email
    const existing = await dbGet('SELECT invite_id FROM invitations WHERE email = ?', [email]);
    
    if (existing) {
      ctx.body = {
        invite_id: existing.invite_id,
        message: 'Invitation already exists for this email.'
      };
      return;
    }

    // Create new invitation
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
    ctx.throw(400, 'invite_id, user_name, and password are required');
  }

  try {
    // 1. Validate invitation
    const invite = await dbGet('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id]);
    if (!invite) {
      ctx.status = 401;
      ctx.body = { message: 'Invalid invite_id' };
      return;
    }

    // 2. Check if username already exists
    const userExists = await dbGet('SELECT id FROM users WHERE user_name = ?', [user_name]);
    if (userExists) {
      ctx.status = 400;
      ctx.body = { message: 'Username already exists. Try providing different username.' };
      return;
    }

    // 3. Hash password and create user
    const hashedPassword = await bcrypt.hash(password, 10);
    await dbRun('INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)', [user_name, invite.email, hashedPassword]);

    // 4. Mark invitation as used
    await dbRun('UPDATE invitations SET used = 1 WHERE invite_id = ?', [invite_id]);

    ctx.body = { message: 'User created successfully' };
  } catch (err) {
    ctx.throw(500, err.message);
  }
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});