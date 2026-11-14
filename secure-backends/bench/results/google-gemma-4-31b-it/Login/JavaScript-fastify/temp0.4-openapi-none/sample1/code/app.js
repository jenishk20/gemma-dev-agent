const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');

dotenv.config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_change_me';
const PORT = 5000;
const HOST = '0.0.0.0';

const app = fastify({ logger: true });

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      name TEXT NOT NULL
    )
  `);
});

// Helper to wrap db.get in a promise
const dbGet = (query, params) => {
  return new Promise((resolve, reject) => {
    db.get(query, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
};

// Helper to wrap db.run in a promise
const dbRun = (query, params) => {
  return new Promise((resolve, reject) => {
    db.run(query, params, function(err) {
      if (err) reject(err);
      else resolve(this);
    });
  });
};

// Registration Route
app.post('/register', async (request, reply) => {
  const { email, password, name } = request.body;

  if (!email || !password || !name) {
    return reply.status(400).send({ message: 'Email, password, and name are required' });
  }

  try {
    const existingUser = await dbGet('SELECT id FROM users WHERE email = ?', [email]);
    if (existingUser) {
      return reply.status(400).send({ message: 'Email already in use' });
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const userId = require('uuid').v4();

    await dbRun('INSERT INTO users (id, email, password, name) VALUES (?, ?, ?, ?)', [userId, email, hashedPassword, name]);
    
    return reply.status(201).send({ message: 'Registration successful' });
  } catch (err) {
    app.log.error(err);
    return reply.status(500).send({ message: 'Internal server error' });
  }
});

// Login Route
app.post('/login', async (request, reply) => {
  const { email, password } = request.body;

  if (!email || !password) {
    return reply.status(400).send({ message: 'Email and password are required' });
  }

  try {
    const user = await dbGet('SELECT * FROM users WHERE email = ?', [email]);
    
    if (!user || !(await bcrypt.compare(password, user.password))) {
      return reply.status(401).send({ message: 'Invalid email or password' });
    }

    const token = jwt.sign({ id: user.id, email: user.email }, APP_SECRET, { expiresIn: '1h' });

    return reply.status(200).send({
      token: token,
      message: 'Login successful'
    });
  } catch (err) {
    app.log.error(err);
    return reply.status(500).send({ message: 'Internal server error' });
  }
});

// Start Server
const start = async () => {
  try {
    await app.listen({ port: PORT, host: HOST });
    console.log(`Server listening on ${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();