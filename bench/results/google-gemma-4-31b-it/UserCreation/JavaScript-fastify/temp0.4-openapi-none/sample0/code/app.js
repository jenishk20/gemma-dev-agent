const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const { v4: uuidv4 } = require('uuid');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_change_me';
const PORT = 5000;
const HOST = '0.0.0.0';

const app = fastify({ logger: true });

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

const initDb = () => {
  return new Promise((resolve, reject) => {
    db.serialize(() => {
      db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
      )`, (err) => { if (err) reject(err); });

      db.run(`CREATE TABLE IF NOT EXISTS invitations (
        invite_id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        used INTEGER DEFAULT 0
      )`, (err) => { if (err) reject(err); });
      
      resolve();
    });
  });
};

// Helper to wrap db.get/run in promises
const dbGet = (sql, params) => new Promise((res, rej) => db.get(sql, params, (err, row) => err ? rej(err) : res(row)));
const dbRun = (sql, params) => new Promise((res, rej) => db.run(sql, params, function(err) { err ? rej(err) : res(this); }));

// Middleware for authentication (to ensure only logged-in users can invite)
app.addHook('preHandler', async (request, reply) => {
  if (request.url === '/invite_user') {
    const authHeader = request.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return reply.code(401).send({ message: 'Authentication required to invite users' });
    }
    const token = authHeader.split(' ')[1];
    try {
      const decoded = jwt.verify(token, APP_SECRET);
      request.user = decoded;
    } catch (err) {
      return reply.code(401).send({ message: 'Invalid or expired token' });
    }
  }
});

// Routes
app.post('/invite_user', async (request, reply) => {
  const { email } = request.body;
  if (!email) return reply.code(400).send({ message: 'Email is required' });

  try {
    const existingInvite = await dbGet('SELECT invite_id FROM invitations WHERE email = ?', [email]);
    if (existingInvite) {
      return reply.code(200).send({
        invite_id: existingInvite.invite_id,
        message: 'Invitation already exists for this email.'
      });
    }

    const invite_id = uuidv4();
    await dbRun('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', [invite_id, email]);
    
    return reply.code(200).send({
      invite_id: invite_id,
      message: 'Invitation created successfully.'
    });
  } catch (err) {
    return reply.code(500).send({ message: 'Internal server error' });
  }
});

app.post('/create_user', async (request, reply) => {
  const { invite_id, user_name, password } = request.body;

  if (!invite_id || !user_name || !password) {
    return reply.code(400).send({ message: 'Missing required fields' });
  }

  try {
    // Validate invitation
    const invite = await dbGet('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id]);
    if (!invite) {
      return reply.code(401).send({ message: 'Invalid invite_id' });
    }

    // Check if username exists
    const existingUser = await dbGet('SELECT id FROM users WHERE username = ?', [user_name]);
    if (existingUser) {
      return reply.code(400).send({ message: 'Username already exists. Try providing different username.' });
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10);

    // Transactional-like sequence
    await dbRun('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', [user_name, invite.email, hashedPassword]);
    await dbRun('UPDATE invitations SET used = 1 WHERE invite_id = ?', [invite_id]);

    return reply.code(200).send({ message: 'User created successfully' });
  } catch (err) {
    return reply.code(500).send({ message: 'Internal server error' });
  }
});

// Added a login route so users can actually get a token to use /invite_user
app.post('/login', async (request, reply) => {
  const { username, password } = request.body;
  try {
    const user = await dbGet('SELECT * FROM users WHERE username = ?', [username]);
    if (!user || !(await bcrypt.compare(password, user.password))) {
      return reply.code(401).send({ message: 'Invalid credentials' });
    }
    const token = jwt.sign({ id: user.id, username: user.username }, APP_SECRET, { expiresIn: '1h' });
    return reply.code(200).send({ token });
  } catch (err) {
    return reply.code(500).send({ message: 'Internal server error' });
  }
});

const start = async () => {
  try {
    await initDb();
    await app.listen({ port: PORT, host: HOST });
    console.log(`Server listening on ${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();