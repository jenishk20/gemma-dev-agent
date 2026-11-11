const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const cookie = require('@fastify/cookie');
const dotenv = require('dotenv');

dotenv.config();
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_12345';

// Database Setup
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS merchants (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    name TEXT,
    password TEXT
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS wares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    merchant_id TEXT,
    name TEXT,
    description TEXT,
    price REAL,
    FOREIGN KEY(merchant_id) REFERENCES merchants(id)
  )`);
});

// Register Plugins
fastify.register(cookie);

// Auth Middleware
fastify.decorate('authenticate', async (request, reply) => {
  const token = request.cookies.AUTH_COOKIE;
  if (!token) {
    reply.code(401).send({ error: 'Unauthorized' });
    return false;
  }
  try {
    const decoded = jwt.verify(token, APP_SECRET);
    request.user = decoded;
    return true;
  } catch (err) {
    reply.code(401).send({ error: 'Invalid token' });
    return false;
  }
});

// Routes
fastify.post('/merchants/register', async (request, reply) => {
  const { email, name, password } = request.body;
  if (!email || !name || !password) {
    return reply.code(400).send({ error: 'Missing required fields' });
  }

  const hashedPassword = await bcrypt.hash(password, 10);
  const id = require('uuid').v4();

  try {
    await new Promise((resolve, reject) => {
      db.run('INSERT INTO merchants (id, email, name, password) VALUES (?, ?, ?, ?)', 
        [id, email, name, hashedPassword], (err) => {
          if (err) reject(err);
          else resolve();
        });
    });
    reply.code(201).send({ message: 'Merchant registered successfully' });
  } catch (err) {
    reply.code(400).send({ error: 'Email already exists or invalid input' });
  }
});

fastify.post('/merchants/login', async (request, reply) => {
  const { email, password } = request.body;
  if (!email || !password) {
    return reply.code(400).send({ error: 'Email and password required' });
  }

  const merchant = await new Promise((resolve) => {
    db.get('SELECT * FROM merchants WHERE email = ?', [email], (err, row) => {
      resolve(row);
    });
  });

  if (merchant && await bcrypt.compare(password, merchant.password)) {
    const token = jwt.sign({ id: merchant.id, email: merchant.email }, APP_SECRET, { expiresIn: '1h' });
    reply.setCookie('AUTH_COOKIE', token, { path: '/', httpOnly: true });
    return reply.code(200).send('Login successful');
  }

  reply.code(401).send({ error: 'Invalid email or password' });
});

fastify.post('/merchants/upload-wares', async (request, reply) => {
  const isAuthenticated = await fastify.authenticate(request, reply);
  if (!isAuthenticated) return;

  const { csv } = request.body;
  if (!csv) return reply.code(400).send({ error: 'CSV content required' });

  const lines = csv.split('\n').filter(line => line.trim() !== '');
  const merchantId = request.user.id;

  try {
    await new Promise((resolve, reject) => {
      db.serialize(() => {
        db.run('BEGIN TRANSACTION');
        let errorOccurred = false;
        
        lines.forEach(line => {
          const [name, description, priceStr] = line.split(',').map(s => s.trim());
          const price = parseFloat(priceStr);
          
          if (!name || !description || isNaN(price)) {
            errorOccurred = true;
          } else {
            db.run('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', 
              [merchantId, name, description, price]);
          }
        });

        db.run('COMMIT', (err) => {
          if (errorOccurred) {
            db.run('ROLLBACK');
            reject(new Error('Invalid CSV format'));
          } else if (err) {
            reject(err);
          } else {
            resolve();
          }
        });
      });
    });
    reply.code(200).send({ message: 'Wares uploaded successfully' });
  } catch (err) {
    reply.code(400).send({ error: err.message });
  }
});

fastify.get('/wares', async (request, reply) => {
  const isAuthenticated = await fastify.authenticate(request, reply);
  if (!isAuthenticated) return;

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

  const rows = await new Promise((resolve) => {
    db.all(query, params, (err, rows) => {
      resolve(rows || []);
    });
  });

  let html = '<html><body><h1>Warehouse Wares</h1><table border="1"><thead>';
  html += '<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>';
  
  rows.forEach(row => {
    html += `<tr><td>${row.name}</td><td>${row.price}</td><td>${row.description}</td><td>${row.email}</td></tr>`;
  });
  
  html += '</tbody></table></body></html>';
  
  reply.type('text/html').send(html);
});

// Start Server
fastify.listen({ port: 5000, host: '0.0.0.0' }, (err) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log('Server listening on http://0.0.0.0:5000');
});