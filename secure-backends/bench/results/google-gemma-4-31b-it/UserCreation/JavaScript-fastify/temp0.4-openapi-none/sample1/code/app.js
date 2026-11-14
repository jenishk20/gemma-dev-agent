const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');
const dotenv = require('dotenv');

dotenv.config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_change_me';
const PORT = 5000;
const HOST = '0.0.0.0';

const app = fastify({ logger: true });

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

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

// Helper to wrap db.get/run in promises
const dbGet = (query, params) => new Promise((res, rej) => {
  db.get(query, params, (err, row) => err ? rej(err) : res(row));
});

const dbRun = (query, params) => new Promise((res, rej) => {
  db.run(query, params, function(err) { err ? rej(err) : res(this); });
});

// Route: /invite_user
app.post('/invite_user', async (request, reply) => {
  const { email } = request.body;

  if (!email) {
    return reply.status(400).send({ message: "Email is required" });
  }

  try {
    const existingInvite = await dbGet('SELECT invite_id FROM invitations WHERE email = ?', [email]);

    if (existingInvite) {
      return reply.status(200).send({
        invite_id: existingInvite.invite_id,
        message: "Invitation already exists for this email."
      });
    }

    const invite_id = uuidv4();
    await dbRun('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', [invite_id, email]);

    return reply.status(200).send({
      invite_id: invite_id,
      message: "Invitation created successfully."
    });
  } catch (error) {
    app.log.error(error);
    return reply.status(500).send({ message: "Internal server error" });
  }
});

// Route: /create_user
app.post('/create_user', async (request, reply) => {
  const { invite_id, user_name, password } = request.body;

  if (!invite_id || !user_name || !password) {
    return reply.status(400).send({ message: "Missing required fields: invite_id, user_name, or password" });
  }

  try {
    // 1. Validate invitation
    const invite = await dbGet('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id]);
    if (!invite) {
      return reply.status(401).send({ message: "Invalid invite_id" });
    }

    // 2. Check if username already exists
    const existingUser = await dbGet('SELECT id FROM users WHERE user_name = ?', [user_name]);
    if (existingUser) {
      return reply.status(400).send({ message: "Username already exists. Try providing different username." });
    }

    // 3. Hash password and create user
    const hashedPassword = await bcrypt.hash(password, 10);
    await dbRun('INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)', [user_name, invite.email, hashedPassword]);

    // 4. Mark invitation as used
    await dbRun('UPDATE invitations SET used = 1 WHERE invite_id = ?', [invite_id]);

    return reply.status(200).send({ message: "User created successfully" });
  } catch (error) {
    app.log.error(error);
    return reply.status(500).send({ message: "Internal server error" });
  }
});

const start = async () => {
  try {
    await initDb();
    await app.listen({ port: PORT, host: HOST });
    console.log(`Server listening on http://${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();