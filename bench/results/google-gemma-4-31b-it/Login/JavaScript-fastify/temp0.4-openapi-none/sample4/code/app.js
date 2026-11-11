const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_change_me';
const PORT = 5000;
const HOST = '0.0.0.0';

// Initialize Database
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    password TEXT,
    name TEXT
  )`);
});

// Helper to wrap db.get/run in promises
const dbGet = (query, params) => new Promise((res, rej) => {
  db.get(query, params, (err, row) => err ? rej(err) : res(row));
});
const dbRun = (query, params) => new Promise((res, rej) => {
  db.run(query, params, function(err) { err ? rej(err) : res(this); });
});

// Registration Endpoint
fastify.post('/register', async (request, reply) => {
  const { email, password, name } = request.body;

  if (!email || !password || !name) {
    return reply.code(400).send({ message: 'Email, password, and name are required' });
  }

  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    const userId = require('uuid').v4();

    await dbRun('INSERT INTO users (id, email, password, name) VALUES (?, ?, ?, ?)', [userId, email, hashedPassword, name]);
    
    return reply.code(201).send({ message: 'Registration successful' });
  } catch (err) {
    if (err.message.includes('UNIQUE constraint failed')) {
      return reply.code(400).send({ message: 'Email already in use' });
    }
    return reply.code(500).send({ message: 'Internal server error' });
  }
});

// Login Endpoint
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

    const token = jwt.sign({ id: user.id, email: user.email }, APP_SECRET, { expiresIn: '1h' });

    return reply.code(200).send({
      token: token,
      message: 'Login successful'
    });
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