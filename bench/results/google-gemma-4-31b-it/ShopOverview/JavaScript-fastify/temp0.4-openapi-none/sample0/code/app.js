const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const fastifyCookie = require('@fastify/cookie');
require('dotenv').config();

const APP_SECRET = process.env.APP_SECRET || 'default_secret_key';
const PORT = 5000;
const HOST = '0.0.0.0';

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

// Plugins
fastify.register(fastifyCookie, {
  secret: APP_SECRET
});

// Auth Helper
const authenticate = async (request, reply) => {
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
    reply.code(401).send({ error: 'Unauthorized' });
    return false;
  }
};

// Routes
fastify.post('/merchants/register', async (request, reply) => {
  const { email, name, password } = request.body;
  if (!email || !name || !password) {
    return reply.code(400).send({ error: 'Invalid input' });
  }

  const hashedPassword = await bcrypt.hash(password, 10);
  const id = require('uuid').v4();

  return new Promise((resolve, reject) => {
    db.run('INSERT INTO merchants (id, email, name, password) VALUES (?, ?, ?, ?)', 
      [id, email, name, hashedPassword], 
      (err) => {
        if (err) {
          resolve(reply.code(400).send({ error: 'Merchant already exists or invalid input' }));
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
    db.get('SELECT * FROM merchants WHERE email = ?', [email], async (err, merchant) => {
      if (err || !merchant || !(await bcrypt.compare(password, merchant.password))) {
        resolve(reply.code(401).send({ error: 'Invalid email or password' }));
      } else {
        const token = jwt.sign({ id: merchant.id, email: merchant.email }, APP_SECRET, { expiresIn: '1h' });
        reply.setCookie('AUTH_COOKIE', token, { httpOnly: true, path: '/' });
        resolve(reply.code(200).send('Login successful'));
      }
    });
  });
});

fastify.post('/merchants/upload-wares', async (request, reply) => {
  if (!(await authenticate(request, reply))) return;

  const { csv } = request.body;
  if (!csv) return reply.code(400).send({ error: 'CSV string required' });

  const lines = csv.split('\n').filter(line => line.trim() !== '');
  const merchantId = request.user.id;

  const stmt = db.prepare('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)');
  
  try {
    db.run('BEGIN TRANSACTION');
    for (const line of lines) {
      const [name, description, priceStr] = line.split(',').map(s => s.trim());
      const price = parseFloat(priceStr);
      if (!name || !description || isNaN(price)) {
        throw new Error('Invalid CSV format');
      }
      stmt.run([merchantId, name, description, price]);
    }
    stmt.finalize();
    db.run('COMMIT', (err) => {
      if (err) return reply.code(500).send({ error: 'Database error' });
      reply.code(200).send({ message: 'Wares uploaded successfully' });
    });
  } catch (e) {
    db.run('ROLLBACK');
    reply.code(400).send({ error: e.message });
  }
});

fastify.get('/wares', async (request, reply) => {
  if (!(await authenticate(request, reply))) return;

  const { minPrice, maxPrice } = request.query;
  let query = `
    SELECT w.name, w.description, w.price, m.email 
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
        resolve(reply.code(500).send({ error: 'Database error' }));
        return;
      }

      let html = '<html><body><h1>Warehouse Wares</h1><table border="1"><thead>';
      html += '<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>';
      
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
fastify.listen({ port: PORT, host: HOST }, (err, address) => {
  if (err) {
    fastify.log.error(err);
    process.exit(1);
  }
  console.log(`Server listening at ${address}`);
});