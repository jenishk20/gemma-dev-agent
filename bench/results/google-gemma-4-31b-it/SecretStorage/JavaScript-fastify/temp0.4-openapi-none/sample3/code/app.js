const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');

dotenv.config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_change_me';
const PORT = 5000;
const HOST = '0.0.0.0';

// Database Initialization
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

// Helper to wrap db.get/run in promises
const dbGet = (query, params) => new Promise((res, rej) => {
  db.get(query, params, (err, row) => err ? rej(err) : res(row));
});
const dbRun = (query, params) => new Promise((res, rej) => {
  db.run(query, params, function(err) { err ? rej(err) : res(this); });
});

// Authentication Middleware
const authenticate = async (request, reply) => {
  try {
    const authHeader = request.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new Error('Missing token');
    }
    const token = authHeader.split(' ')[1];
    const decoded = jwt.verify(token, APP_SECRET);
    request.user = decoded;
  } catch (err) {
    reply.code(401).send({ message: 'Invalid authentication token' });
    return false;
  }
  return true;
};

// Routes
fastify.post('/register', async (request, reply) => {
  const { email, username, password } = request.body;
  if (!email || !username || !password) {
    return reply.code(400).send({ message: 'Email, username and password are required' });
  }

  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    await dbRun('INSERT INTO users (email, username, password) VALUES (?, ?, ?)', [email, username, hashedPassword]);
    return reply.code(201).send({ message: 'Registration successful' });
  } catch (err) {
    return reply.code(400).send({ message: 'Email already in use or invalid data' });
  }
});

fastify.post('/login', async (request, reply) => {
  const { email, password } = request.body;
  if (!email || !password) {
    return reply.code(400).send({ message: 'Email and password are required' });
  }

  try {
    const user = await dbGet('SELECT * FROM users WHERE email = ?', [email]);
    if (!user || !(await bcrypt.compare(password, user.password))) {
      return reply.code(401).send({ message: 'Invalid email or password' });
    }

    const token = jwt.sign({ username: user.username, email: user.email }, APP_SECRET, { expiresIn: '24h' });
    return reply.code(200).send({ token, message: 'Login successful' });
  } catch (err) {
    return reply.code(500).send({ message: 'Internal server error' });
  }
});

fastify.post('/set_secret', async (request, reply) => {
  if (!(await authenticate(request, reply))) return;

  const { username, secret } = request.body;
  if (!username || secret === undefined) {
    return reply.code(400).send({ message: 'Username and secret are required' });
  }

  // Security check: ensure user can only set secret for their own account
  if (request.user.username !== username) {
    return reply.code(401).send({ message: 'Unauthorized to set secret for this user' });
  }

  try {
    await dbRun('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', [username, secret]);
    return reply.code(200).send({ message: 'Secret has been set successfully' });
  } catch (err) {
    return reply.code(500).send({ message: 'Internal server error' });
  }
});

fastify.get('/get_secret', async (request, reply) => {
  if (!(await authenticate(request, reply))) return;

  const { username } = request.query;
  if (!username) {
    return reply.code(400).send({ message: 'Username query parameter is required' });
  }

  // Security check: ensure user can only retrieve their own secret
  if (request.user.username !== username) {
    return reply.code(401).send({ message: 'Unauthorized to retrieve secret for this user' });
  }

  try {
    const row = await dbGet('SELECT secret_value FROM secrets WHERE username = ?', [username]);
    if (!row) {
      return reply.code(404).send({ message: 'Secret not found' });
    }
    return reply.code(200).send({ secret: row.secret_value });
  } catch (err) {
    return reply.code(500).send({ message: 'Internal server error' });
  }
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ port: PORT, host: HOST });
    console.log(`Server listening on http://${HOST}:${PORT}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();