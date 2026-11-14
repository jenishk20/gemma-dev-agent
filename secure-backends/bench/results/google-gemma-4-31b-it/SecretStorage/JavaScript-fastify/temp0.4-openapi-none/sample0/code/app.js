const fastify = require('fastify')({ logger: false });
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
    email TEXT UNIQUE,
    username TEXT UNIQUE,
    password TEXT
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS secrets (
    username TEXT PRIMARY KEY,
    secret_value TEXT,
    FOREIGN KEY(username) REFERENCES users(username)
  )`);
});

// Helper to wrap db.get/run in promises
const dbGet = (sql, params = []) => new Promise((res, rej) => {
  db.get(sql, params, (err, row) => err ? rej(err) : res(row));
});
const dbRun = (sql, params = []) => new Promise((res, rej) => {
  db.run(sql, params, function(err) { err ? rej(err) : res(this); });
});

// Authentication Middleware
fastify.addHook('preHandler', async (request, reply) => {
  const publicRoutes = ['/register', '/login'];
  if (publicRoutes.includes(request.url)) return;

  const authHeader = request.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return reply.code(401).send({ message: 'Invalid authentication token' });
  }

  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, APP_SECRET);
    request.user = decoded;
  } catch (err) {
    return reply.code(401).send({ message: 'Invalid authentication token' });
  }
});

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

  const user = await dbGet('SELECT * FROM users WHERE email = ?', [email]);
  if (!user || !(await bcrypt.compare(password, user.password))) {
    return reply.code(401).send({ message: 'Invalid email or password' });
  }

  const token = jwt.sign({ username: user.username, email: user.email }, APP_SECRET, { expiresIn: '24h' });
  return reply.code(200).send({ token, message: 'Login successful' });
});

fastify.post('/set_secret', async (request, reply) => {
  const { username, secret } = request.body;
  
  // Security check: ensure user is setting their own secret
  if (request.user.username !== username) {
    return reply.code(401).send({ message: 'Unauthorized to set secret for this user' });
  }

  await dbRun('INSERT INTO secrets (username, secret_value) VALUES (?, ?) ON CONFLICT(username) DO UPDATE SET secret_value = excluded.secret_value', [username, secret]);
  return reply.code(200).send({ message: 'Secret has been set successfully' });
});

fastify.get('/get_secret', async (request, reply) => {
  const { username } = request.query;
  
  if (!username) {
    return reply.code(400).send({ message: 'Username query parameter is required' });
  }

  // Security check: ensure user is retrieving their own secret
  if (request.user.username !== username) {
    return reply.code(401).send({ message: 'Invalid authentication token' });
  }

  const row = await dbGet('SELECT secret_value FROM secrets WHERE username = ?', [username]);
  if (!row) {
    return reply.code(200).send({ secret: 'No secret found for this user' });
  }

  return reply.code(200).send({ secret: row.secret_value });
});

// Start Server
fastify.listen({ port: PORT, host: HOST }, (err) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log(`Server listening on ${HOST}:${PORT}`);
});