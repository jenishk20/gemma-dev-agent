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

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

const initDb = () => {
  return new Promise((resolve, reject) => {
    db.serialize(() => {
      // Invitations table: stores email and a unique invite_id
      db.run(`CREATE TABLE IF NOT EXISTS invitations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        invite_id TEXT UNIQUE NOT NULL,
        used INTEGER DEFAULT 0
      )`, (err) => {
        if (err) reject(err);
      });

      // Users table: stores username, password hash, and email
      db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
      )`, (err) => {
        if (err) reject(err);
        resolve();
      });
    });
  });
};

// Helper to wrap db.get and db.run in promises
const dbGet = (query, params = []) => {
  return new Promise((resolve, reject) => {
    db.get(query, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
};

const dbRun = (query, params = []) => {
  return new Promise((resolve, reject) => {
    db.run(query, params, function (err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
};

// Route: /invite_user
router.post('/invite_user', async (ctx) => {
  const { email } = ctx.request.body;

  if (!email || !email.includes('@')) {
    ctx.throw(400, 'Invalid email address');
  }

  try {
    // Check if invitation already exists for this email
    const existingInvite = await dbGet('SELECT invite_id FROM invitations WHERE email = ?', [email]);

    if (existingInvite) {
      ctx.body = {
        invite_id: existingInvite.invite_id,
        message: 'Invitation already exists for this email.'
      };
      return;
    }

    // Create new invitation
    const invite_id = uuidv4();
    await dbRun('INSERT INTO invitations (email, invite_id) VALUES (?, ?)', [email, invite_id]);

    ctx.body = {
      invite_id: invite_id,
      message: 'Invitation created successfully.'
    };
  } catch (error) {
    ctx.throw(500, 'Internal Server Error');
  }
});

// Route: /create_user
router.post('/create_user', async (ctx) => {
  const { invite_id, user_name, password } = ctx.request.body;

  if (!invite_id || !user_name || !password) {
    ctx.throw(400, 'Missing required fields: invite_id, user_name, and password are required.');
  }

  try {
    // 1. Validate invite_id and check if it's used
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
    await dbRun('INSERT INTO users (user_name, password, email) VALUES (?, ?, ?)', [user_name, hashedPassword, invite.email]);

    // 4. Mark invitation as used
    await dbRun('UPDATE invitations SET used = 1 WHERE invite_id = ?', [invite_id]);

    ctx.body = { message: 'User created successfully' };
  } catch (error) {
    console.error(error);
    ctx.throw(500, 'Internal Server Error');
  }
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

async function start() {
  try {
    await initDb();
    app.listen(PORT, HOST, () => {
      console.log(`Server running on http://${HOST}:${PORT}`);
    });
  } catch (err) {
    console.error('Failed to initialize database:', err);
    process.exit(1);
  }
}

start();