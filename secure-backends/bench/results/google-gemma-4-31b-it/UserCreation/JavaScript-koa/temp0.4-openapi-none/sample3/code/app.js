const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const app = new Koa();
const router = new Router();
const PORT = 5000;
const HOST = '0.0.0.0';
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_12345';

// Database Initialization
const db = new sqlite3.Database('db.sqlite3');

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

/**
 * POST /invite_user
 * Creates an invitation for a specific email.
 */
router.post('/invite_user', async (ctx) => {
  const { email } = ctx.request.body;

  if (!email) {
    ctx.throw(400, 'Email is required');
  }

  const getInvite = () => new Promise((resolve, reject) => {
    db.get('SELECT invite_id FROM invitations WHERE email = ?', [email], (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });

  const createInvite = (id) => new Promise((resolve, reject) => {
    db.run('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', [id, email], function(err) {
      if (err) reject(err);
      else resolve();
    });
  });

  try {
    const existing = await getInvite();
    if (existing) {
      ctx.body = {
        invite_id: existing.invite_id,
        message: 'Invitation already exists for this email.'
      };
      return;
    }

    const inviteId = uuidv4();
    await createInvite(inviteId);
    ctx.body = {
      invite_id: inviteId,
      message: 'Invitation created successfully.'
    };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { message: 'Internal server error' };
  }
});

/**
 * POST /create_user
 * Uses an invite_id to create a new user account.
 */
router.post('/create_user', async (ctx) => {
  const { invite_id, user_name, password } = ctx.request.body;

  if (!invite_id || !user_name || !password) {
    ctx.throw(400, 'invite_id, user_name, and password are required');
  }

  const checkInvite = () => new Promise((resolve, reject) => {
    db.get('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id], (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });

  const checkUserExists = (name) => new Promise((resolve, reject) => {
    db.get('SELECT id FROM users WHERE user_name = ?', [name], (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });

  const createUser = (email, name, pwd) => new Promise((resolve, reject) => {
    db.run('INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)', [name, email, pwd], function(err) {
      if (err) reject(err);
      else resolve();
    });
  });

  const markInviteUsed = (id) => new Promise((resolve, reject) => {
    db.run('UPDATE invitations SET used = 1 WHERE invite_id = ?', [id], (err) => {
      if (err) reject(err);
      else resolve();
    });
  });

  try {
    const invite = await checkInvite();
    if (!invite) {
      ctx.status = 401;
      ctx.body = { message: 'Invalid invite_id' };
      return;
    }

    const existingUser = await checkUserExists(user_name);
    if (existingUser) {
      ctx.status = 400;
      ctx.body = { message: 'Username already exists. Try providing different username.' };
      return;
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    await createUser(invite.email, user_name, hashedPassword);
    await markInviteUsed(invite_id);

    ctx.body = { message: 'User created successfully' };
  } catch (error) {
    ctx.status = 500;
    ctx.body = { message: 'Internal server error' };
  }
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});