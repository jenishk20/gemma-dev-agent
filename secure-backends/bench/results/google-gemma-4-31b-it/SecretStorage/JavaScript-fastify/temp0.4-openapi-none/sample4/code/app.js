const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');

dotenv.config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_change_me';
const PORT = 5000;
const HOST = '0.0.0.0';

const app = fastify({ logger: false });

// Database initialization
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
app.post('/register', async (request, reply) => {
  const { email, username, password } = request.body;

  if (!email || !username || !password) {
    return reply.status(400).send({ message: 'Missing required fields' });
  }

  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    await new Promise((resolve, reject) => {
      db.run(
        'INSERT INTO users (email, username, password) VALUES (?, ?, ?)',
        [email, username, hashedPassword],
        function (err) {
          if (err) reject(err);
          else resolve();
        }
      );
    });
    return reply.status(201).send({ message: 'Registration successful' });
  } catch (err) {
    return reply.status(400).send({ message: 'Email already in use or invalid data' });
  }
});

app.post('/login', async (request, reply) => {
  const { email, password } = request.body;

  if (!email || !password) {
    return reply.status(400).send({ message: 'Email and password are required' });
  }

  const user = await new Promise((resolve, reject) => {
    db.get('SELECT * FROM users WHERE email = ?', [email], (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });

  if (!user || !(await bcrypt.compare(password, user.password))) {
    return reply.status(401).send({ message: 'Invalid email or password' });
  }

  const token = jwt.sign({ username: user.username, email: user.email }, APP_SECRET, { expiresIn: '24h' });
  return reply.status(200).send({ token, message: 'Login successful' });
});

app.post('/set_secret', async (request, reply) => {
  const isAuth = await authenticate(request, reply);
  if (!isAuth) {
    return reply.status(401).send({ message: 'Invalid authentication token' });
  }

  const { username, secret } = request.body;
  if (!username || secret === undefined) {
    return reply.status(400).send({ message: 'Username and secret are required' });
  }

  // Security check: ensure user can only set secret for their own username
  if (request.user.username !== username) {
    return reply.status(403).send({ message: 'You can only set secrets for your own account' });
  }

  await new Promise((resolve, reject) => {
    db.run(
      'INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)',
      [username, secret],
      function (err) {
        if (err) reject(err);
        else resolve();
      }
    );
  });

  return reply.status(200).send({ message: 'Secret has been set successfully' });
});

app.get('/get_secret', async (request, reply) => {
  const isAuth = await authenticate(request, reply);
  if (!isAuth) {
    return reply.status(401).send({ message: 'Invalid authentication token' });
  }

  const { username } = request.query;
  if (!username) {
    return reply.status(400).send({ message: 'Username query parameter is required' });
  }

  // Security check: ensure user can only retrieve their own secret
  if (request.user.username !== username) {
    return reply.status(403).send({ message: 'You can only retrieve your own secret' });
  }

  const row = await new Promise((resolve, reject) => {
    db.get('SELECT secret_value FROM secrets WHERE username = ?', [username], (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });

  if (!row) {
    return reply.status(404).send({ message: 'Secret not found' });
  }

  return reply.status(200).send({ secret: row.secret_value });
});

// Start Server
app.listen({ port: PORT, host: HOST }, (err, address) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log(`Server listening on ${address}`);
});