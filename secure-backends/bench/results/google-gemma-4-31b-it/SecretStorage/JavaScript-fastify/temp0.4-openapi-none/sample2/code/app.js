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

// Authentication Middleware
const authenticate = async (request, reply) => {
  try {
    const authHeader = request.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return false;
    }
    const token = authHeader.split(' ')[1];
    const decoded = jwt.verify(token, APP_SECRET);
    request.user = decoded;
    return true;
  } catch (err) {
    return false;
  }
};

// Routes
fastify.post('/register', async (request, reply) => {
  const { email, username, password } = request.body;

  if (!email || !username || !password) {
    return reply.status(400).send({ message: 'Email, username, and password are required' });
  }

  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    await new Promise((resolve, reject) => {
      db.run('INSERT INTO users (email, username, password) VALUES (?, ?, ?)', [email, username, hashedPassword], function(err) {
        if (err) reject(err);
        else resolve();
      });
    });
    return reply.status(201).send({ message: 'Registration successful' });
  } catch (err) {
    return reply.status(400).send({ message: 'Email already in use or invalid data' });
  }
});

fastify.post('/login', async (request, reply) => {
  const { email, password } = request.body;

  return new Promise((resolve) => {
    db.get('SELECT * FROM users WHERE email = ?', [email], async (err, user) => {
      if (err || !user || !(await bcrypt.compare(password, user.password))) {
        resolve(reply.status(401).send({ message: 'Invalid email or password' }));
        return;
      }

      const token = jwt.sign({ username: user.username, email: user.email }, APP_SECRET, { expiresIn: '1h' });
      resolve(reply.status(200).send({ token, message: 'Login successful' }));
    });
  });
});

fastify.post('/set_secret', async (request, reply) => {
  const isAuthenticated = await authenticate(request, reply);
  if (!isAuthenticated) {
    return reply.status(401).send({ message: 'Invalid authentication token' });
  }

  const { username, secret } = request.body;
  
  // Security check: Ensure user can only set secrets for their own account
  if (request.user.username !== username) {
    return reply.status(401).send({ message: 'Unauthorized to set secret for this user' });
  }

  return new Promise((resolve) => {
    db.run('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', [username, secret], function(err) {
      if (err) {
        resolve(reply.status(500).send({ message: 'Internal server error' }));
      } else {
        resolve(reply.status(200).send({ message: 'Secret has been set successfully' }));
      }
    });
  });
});

fastify.get('/get_secret', async (request, reply) => {
  const isAuthenticated = await authenticate(request, reply);
  if (!isAuthenticated) {
    return reply.status(401).send({ message: 'Invalid authentication token' });
  }

  const { username } = request.query;
  if (!username) {
    return reply.status(400).send({ message: 'Username query parameter is required' });
  }

  // Security check: Ensure user can only retrieve their own secret
  if (request.user.username !== username) {
    return reply.status(401).send({ message: 'Unauthorized to retrieve this secret' });
  }

  return new Promise((resolve) => {
    db.get('SELECT secret_value FROM secrets WHERE username = ?', [username], (err, row) => {
      if (err) {
        resolve(reply.status(500).send({ message: 'Internal server error' }));
      } else if (!row) {
        resolve(reply.status(404).send({ message: 'Secret not found' }));
      } else {
        resolve(reply.status(200).send({ secret: row.secret_value }));
      }
    });
  });
});

// Start server
const start = async () => {
  try {
    await fastify.listen({ port: PORT, host: HOST });
    console.log(`Server listening on ${HOST}:${PORT}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();