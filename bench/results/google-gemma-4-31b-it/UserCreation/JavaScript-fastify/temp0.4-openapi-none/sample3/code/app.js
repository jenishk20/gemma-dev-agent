const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_change_me';
const DB_PATH = 'db.sqlite3';

// Database initialization
const db = new sqlite3.Database(DB_PATH);

const initDb = () => {
  return new Promise((resolve, reject) => {
    db.serialize(() => {
      db.run(`CREATE TABLE IF NOT EXISTS invitations (
        invite_id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        used INTEGER DEFAULT 0
      )`, (err) => {
        if (err) reject(err);
      });
      db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
      )`, (err) => {
        if (err) reject(err);
        resolve();
      });
    });
  });
};

// Helper for DB queries
const dbGet = (query, params = []) => new Promise((resolve, reject) => {
  db.get(query, params, (err, row) => {
    if (err) reject(err);
    else resolve(row);
  });
});

const dbRun = (query, params = []) => new Promise((resolve, reject) => {
  db.run(query, params, function(err) {
    if (err) reject(err);
    else resolve(this);
  });
});

// Routes
fastify.post('/invite_user', async (request, reply) => {
  const { email } = request.body;

  if (!email) {
    return reply.status(400).send({ message: 'Email is required' });
  }

  try {
    const existingInvite = await dbGet('SELECT invite_id FROM invitations WHERE email = ?', [email]);

    if (existingInvite) {
      return reply.status(200).send({
        invite_id: existingInvite.invite_id,
        message: 'Invitation already exists for this email.'
      });
    }

    const invite_id = uuidv4();
    await dbRun('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', [invite_id, email]);

    return reply.status(200).send({
      invite_id: invite_id,
      message: 'Invitation created successfully.'
    });
  } catch (err) {
    return reply.status(500).send({ message: 'Internal server error' });
  }
});

fastify.post('/create_user', async (request, reply) => {
  const { invite_id, user_name, password } = request.body;

  if (!invite_id || !user_name || !password) {
    return reply.status(400).send({ message: 'Missing required fields: invite_id, user_name, and password are required.' });
  }

  try {
    // 1. Validate invitation
    const invite = await dbGet('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id]);
    if (!invite) {
      return reply.status(401).send({ message: 'Invalid invite_id' });
    }

    // 2. Check if username exists
    const existingUser = await dbGet('SELECT id FROM users WHERE user_name = ?', [user_name]);
    if (existingUser) {
      return reply.status(400).send({ message: 'Username already exists. Try providing different username.' });
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

    return reply.status(200).send({ message: 'User created' });
  } catch (err) {
    fastify.log.error(err);
    return reply.status(500).send({ message: 'Internal server error' });
  }
});

// Start server
const start = async () => {
  try {
    await initDb();
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();