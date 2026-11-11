const fastify = require('fastify')({ logger: false });
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const cookie = require('@fastify/cookie');
const { v4: uuidv4 } = require('uuid');
require('dotenv').config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_12345';
const DB_PATH = './db.sqlite3';

// Database Initialization
const db = new sqlite3.Database(DB_PATH);

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS merchants (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT,
    password TEXT
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS wares (
    id TEXT PRIMARY KEY,
    merchant_id TEXT,
    name TEXT,
    description TEXT,
    price REAL,
    FOREIGN KEY(merchant_id) REFERENCES merchants(id)
  )`);
});

// Register Plugins
fastify.register(cookie, {
  secret: APP_SECRET
});

// Authentication Middleware
const authenticate = async (request, reply) => {
  const token = request.cookies.AUTH_COOKIE;
  if (!token) {
    return reply.code(401).send({ error: 'Unauthorized' });
  }
  try {
    const decoded = jwt.verify(token, APP_SECRET);
    request.user = decoded;
  } catch (err) {
    return reply.code(401).send({ error: 'Invalid or expired token' });
  }
};

// Routes
fastify.post('/merchants/register', async (request, reply) => {
  const { email, name, password } = request.body;
  if (!email || !name || !password) {
    return reply.code(400).send({ error: 'Missing required fields' });
  }

  const hashedPassword = await bcrypt.hash(password, 10);
  const id = uuidv4();

  return new Promise((resolve, reject) => {
    db.run('INSERT INTO merchants (id, email, name, password) VALUES (?, ?, ?, ?)', 
      [id, email, name, hashedPassword], 
      function(err) {
        if (err) {
          if (err.message.includes('UNIQUE constraint failed')) {
            resolve(reply.code(400).send({ error: 'Email already registered' }));
          } else {
            resolve(reply.code(500).send(err));
          }
        } else {
          resolve(reply.code(201).send({ message: 'Merchant registered successfully' }));
        }
      }
    );
  });
});

fastify.post('/merchants/login', async (request, reply) => {
  const { email, password } = request.body;
  if (!email || !password) {
    return reply.code(400).send({ error: 'Email and password required' });
  }

  return new Promise((resolve) => {
    db.get('SELECT * FROM merchants WHERE email = ?', [email], async (err, user) => {
      if (err || !user || !(await bcrypt.compare(password, user.password))) {
        resolve(reply.code(401).send({ error: 'Invalid email or password' }));
      } else {
        const token = jwt.sign({ id: user.id, email: user.email }, APP_SECRET, { expiresIn: '24h' });
        reply.setCookie('AUTH_COOKIE', token, { httpOnly: true, path: '/' });
        resolve(reply.code(200).send('Login successful'));
      }
    });
  });
});

fastify.post('/merchants/upload-wares', { preHandler: [authenticate] }, async (request, reply) => {
  const { csv } = request.body;
  if (!csv) return reply.code(400).send({ error: 'CSV data is required' });

  const lines = csv.split('\n').filter(line => line.trim() !== '');
  const merchantId = request.user.id;
  
  const waresToInsert = [];
  for (const line of lines) {
    const [name, description, priceStr] = line.split(',').map(s => s?.trim());
    const price = parseFloat(priceStr);
    if (!name || !description || isNaN(price)) {
      return reply.code(400).send({ error: 'Invalid CSV format. Expected: name, description, price' });
    }
    waresToInsert.push({ id: uuidv4(), merchantId, name, description, price });
  }

  return new Promise((resolve) => {
    db.serialize(() => {
      db.run('BEGIN TRANSACTION');
      const stmt = db.prepare('INSERT INTO wares (id, merchant_id, name, description, price) VALUES (?, ?, ?, ?, ?)');
      waresToInsert.forEach(w => stmt.run(w.id, w.merchantId, w.name, w.description, w.price));
      stmt.finalize();
      db.run('COMMIT', (err) => {
        if (err) resolve(reply.code(500).send(err));
        else resolve(reply.code(200).send({ message: 'Wares uploaded successfully' }));
      });
    });
  });
});

fastify.get('/wares', { preHandler: [authenticate] }, async (request, reply) => {
  const { minPrice, maxPrice } = request.query;
  let query = `
    SELECT w.name, w.price, w.description, m.email 
    FROM wares w 
    JOIN merchants m ON w.merchant_id = m.id 
    WHERE 1=1
  `;
  const params = [];

  if (minPrice) {
    query += ' AND w.price >= ?';
    params.push(parseFloat(minPrice));
  }
  if (maxPrice) {
    query += ' AND w.price <= ?';
    params.push(parseFloat(maxPrice));
  }

  return new Promise((resolve) => {
    db.all(query, params, (err, rows) => {
      if (err) {
        resolve(reply.code(500).send(err));
        return;
      }

      let html = '<html><body><h1>Warehouse Wares</h1><table border="1"><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>';
      rows.forEach(row => {
        html += `<tr><td>${row.name}</td><td>${row.price}</td><td>${row.description}</td><td>${row.email}</td></tr>`;
      });
      html += '</tbody></table></body></html>';
      
      reply.type('text/html').send(html);
      resolve();
    });
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();