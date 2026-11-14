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

// Authentication Middleware
const authenticate = async (request, reply) => {
  const authHeader = request.headers.authorization;
  if (!authHeader) {
    reply.code(401).send({ message: 'Invalid authentication token' });
    return;
  }

  const token = authHeader.replace('Bearer ', '');
  try {
    const decoded = jwt.verify(token, APP_SECRET);
    request.user = decoded;
  } catch (err) {
    reply.code(401).send({ message: 'Invalid authentication token' });
  }
};

// Routes
fastify.post('/register', async (request, reply) => {
  const { email, username, password } = request.body;

  if (!email || !username || !password) {
    return reply.code(400).send({ message: 'Email, username, and password are required' });
  }

  const hashedPassword = await bcrypt.hash(password, 10);

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT INTO users (username, email, password) VALUES (?, ?, ?)');
    stmt.run(username, email, hashedPassword, function (err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          resolve(reply.code(400).send({ message: 'Email already in use or invalid data' }));
        } else {
          resolve(reply.code(500).send({ message: 'Internal Server Error' }));
        }
      } else {
        resolve(reply.code(201).send({ message: 'Registration successful' }));
      }
    });
    stmt.finalize();
  });
});

fastify.post('/login', async (request, reply) => {
  const { email, password } = request.body;

  return new Promise((resolve) => {
    db.get('SELECT * FROM users WHERE email = ?', [email], async (err, user) => {
      if (err || !user) {
        return resolve(reply.code(401).send({ message: 'Invalid email or password' }));
      }

      const match = await bcrypt.compare(password, user.password);
      if (!match) {
        return resolve(reply.code(401).send({ message: 'Invalid email or password' }));
      }

      const token = jwt.sign({ username: user.username, email: user.email }, APP_SECRET, { expiresIn: '24h' });
      resolve(reply.code(200).send({ token, message: 'Login successful' }));
    });
  });
});

fastify.post('/set_secret', { preHandler: [authenticate] }, async (request, reply) => {
  const { username, secret } = request.body;

  if (!username || secret === undefined) {
    return reply.code(400).send({ message: 'Username and secret are required' });
  }

  // Security check: User can only set secret for their own username
  if (request.user.username !== username) {
    return reply.code(401).send({ message: 'Unauthorized to set secret for this user' });
  }

  return new Promise((resolve) => {
    db.run('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', [username, secret], function (err) {
      if (err) {
        resolve(reply.code(500).send({ message: 'Database error' }));
      } else {
        resolve(reply.code(200).send({ message: 'Secret has been set successfully' }));
      }
    });
  });
});

fastify.get('/get_secret', { preHandler: [authenticate] }, async (request, reply) => {
  const { username } = request.query;

  if (!username) {
    return reply.code(400).send({ message: 'Username query parameter is required' });
  }

  // Security check: User can only retrieve their own secret
  if (request.user.username !== username) {
    return reply.code(401).send({ message: 'Invalid authentication token' });
  }

  return new Promise((resolve) => {
    db.get('SELECT secret_value FROM secrets WHERE username = ?', [username], (err, row) => {
      if (err) {
        resolve(reply.code(500).send({ message: 'Database error' }));
      } else if (!row) {
        resolve(reply.code(404).send({ message: 'Secret not found' }));
      } else {
        resolve(reply.code(200).send({ secret: row.secret_value }));
      }
    });
  });
});

// Start Server
fastify.listen({ port: PORT, host: HOST }, (err, address) => {
  if (err) {
    fastify.log.error(err);
    process.exit(1);
  }
  console.log(`Server listening on ${address}`);
});