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

app.use(bodyParser());

// Helper to wrap db.get/run in promises
const dbGet = (query, params = []) => new Promise((resolve, reject) => {
  db.get(query, params, (err, row) => err ? reject(err) : resolve(row));
});

const dbRun = (query, params = []) => new Promise((resolve, reject) => {
  db.run(query, params, function(err) { err ? reject(err) : resolve(this); });
});

/**
 * POST /invite_user
 * Creates or retrieves an invitation ID for a specific email.
 */
router.post('/invite_user', async (ctx) => {
  const { email } = ctx.request.body;

  if (!email || !email.includes('@')) {
    ctx.throw(400, 'Valid email is required');
  }

  try {
    const existingInvite = await dbGet('SELECT invite_id FROM invitations WHERE email = ?', [email]);
    
    if (existingInvite) {
      ctx.body = {
        invite_id: existingInvite.invite_id,
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
    ctx.throw(500, 'Internal Server Error');
  }
});

/**
 * POST /create_user
 * Creates a user account using a valid invitation ID.
 */
router.post('/create_user', async (ctx) => {
  const { invite_id, user_name, password } = ctx.request.body;

  if (!invite_id || !user_name || !password) {
    ctx.throw(400, 'Missing required fields: invite_id, user_name, or password');
  }

  try {
    // 1. Validate Invitation
    const invite = await dbGet('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id]);
    if (!invite) {
      ctx.status = 401;
      ctx.body = { message: 'Invalid invite_id' };
      return;
    }

    // 2. Check if username already exists
    const existingUser = await dbGet('SELECT id FROM users WHERE user_name = ?', [user_name]);
    if (existingUser) {
      ctx.status = 400;
      ctx.body = { message: 'Username already exists. Try providing different username.' };
      return;
    }

    // 3. Hash password and create user
    const hashedPassword = await bcrypt.hash(password, 10);
    await dbRun('INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)', [user_name, invite.email, hashedPassword]);

    // 4. Mark invitation as used
    await dbRun('UPDATE invitations SET used = 1 WHERE invite_id = ?', [invite_id]);

    ctx.body = { message: 'User created' };
  } catch (err) {
    console.error(err);
    ctx.throw(500, 'Internal Server Error');
  }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});