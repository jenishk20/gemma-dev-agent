const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
require('dotenv').config();

const APP_SECRET = process.env.APP_SECRET || 'default-secret-key-12345';
const PORT = 5000;
const HOST = '0.0.0.0';

// Initialize SQLite Database
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    name TEXT
  )`);
});

// Registration Endpoint
fastify.post('/register', async (request, reply) => {
  const { email, password, name } = request.body;

  if (!email || !password || !name) {
    return reply.code(400).send({ message: 'Email, password, and name are required' });
  }

  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    
    return new Promise((resolve, reject) => {
      const stmt = db.prepare('INSERT INTO users (email, password, name) VALUES (?, ?, ?)');
      stmt.run(email, hashedPassword, name, function (err) {
        if (err) {
          if (err.message.includes('UNIQUE constraint failed')) {
            resolve(reply.code(400).send({ message: 'Email already in use' }));
          } else {
            resolve(reply.code(500).send({ message: 'Internal server error' }));
          }
        } else {
          resolve(reply.code(201).send({ message: 'Registration successful' }));
        }
      });
      stmt.finalize();
    });
  } catch (error) {
    return reply.code(500).send({ message: 'Internal server error' });
  }
});

// Login Endpoint
fastify.post('/login', async (request, reply) => {
  const { email, password } = request.body;

  if (!email || !password) {
    return reply.code(401).send({ message: 'Email and password are required' });
  }

  return new Promise((resolve) => {
    db.get('SELECT * FROM users WHERE email = ?', [email], async (err, user) => {
      if (err || !user) {
        return resolve(reply.code(401).send({ message: 'Invalid email or password' }));
      }

      const match = await bcrypt.compare(password, user.password);
      if (!match) {
        return resolve(reply.code(401).send({ message: 'Invalid email or password' }));
      }

      const token = jwt.sign({ userId: user.id, email: user.email }, APP_SECRET, { expiresIn: '1h' });
      resolve(reply.code(200).send({
        token: token,
        message: 'Login successful'
      }));
    });
  });
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