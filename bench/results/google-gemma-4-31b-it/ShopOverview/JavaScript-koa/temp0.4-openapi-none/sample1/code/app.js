require('dotenv').config();
const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const session = require('koa-session');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');

const app = new Koa();
const router = new Router();
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key';

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
    id TEXT PRIMARY KEY,
    merchant_id TEXT,
    name TEXT,
    description TEXT,
    price REAL,
    FOREIGN KEY(merchant_id) REFERENCES merchants(id)
  )`);
});

// Session Config
app.keys = [APP_SECRET];
app.use(session({
  key: 'koa.sess:merchant',
  maxAge: 86400000, // 24 hours
  httpOnly: true,
}, true));
app.use(bodyParser());

// Auth Middleware
const authMiddleware = async (ctx, next) => {
  const token = ctx.session.token;
  if (!token) {
    ctx.throw(401, 'Unauthorized');
  }
  try {
    const decoded = jwt.verify(token, APP_SECRET);
    ctx.state.user = decoded;
    await next();
  } catch (err) {
    ctx.throw(401, 'Unauthorized');
  }
};

// Routes
router.post('/merchants/register', async (ctx) => {
  const { email, name, password } = ctx.request.body;
  if (!email || !name || !password) {
    ctx.throw(400, 'Invalid input');
  }

  const hashedPassword = await bcrypt.hash(password, 10);
  const id = uuidv4();

  try {
    await new Promise((resolve, reject) => {
      db.run('INSERT INTO merchants (id, email, name, password) VALUES (?, ?, ?, ?)', 
        [id, email, name, hashedPassword], (err) => {
          if (err) reject(err); else resolve();
        });
    });
    ctx.status = 201;
    ctx.body = 'Merchant registered successfully';
  } catch (err) {
    ctx.throw(400, 'Email already exists');
  }
});

router.post('/merchants/login', async (ctx) => {
  const { email, password } = ctx.request.body;
  if (!email || !password) {
    ctx.throw(400, 'Invalid input');
  }

  const merchant = await new Promise((resolve, reject) => {
    db.get('SELECT * FROM merchants WHERE email = ?', [email], (err, row) => {
      if (err) reject(err); else resolve(row);
    });
  });

  if (merchant && await bcrypt.compare(password, merchant.password)) {
    const token = jwt.sign({ id: merchant.id, email: merchant.email }, APP_SECRET);
    ctx.session.token = token;
    ctx.body = 'Login successful';
  } else {
    ctx.status = 401;
    ctx.body = { error: 'Invalid email or password' };
  }
});

router.post('/merchants/upload-wares', authMiddleware, async (ctx) => {
  const { csv } = ctx.request.body;
  if (!csv) {
    ctx.throw(400, 'CSV content required');
  }

  const lines = csv.split('\n').filter(line => line.trim() !== '');
  const merchantId = ctx.state.user.id;

  try {
    await new Promise((resolve, reject) => {
      db.serialize(() => {
        db.run('BEGIN TRANSACTION');
        let errorOccurred = false;
        
        lines.forEach(line => {
          const [name, description, priceStr] = line.split(',').map(s => s?.trim());
          const price = parseFloat(priceStr);
          
          if (!name || !description || isNaN(price)) {
            errorOccurred = true;
          } else {
            db.run('INSERT INTO wares (id, merchant_id, name, description, price) VALUES (?, ?, ?, ?, ?)', 
              [uuidv4(), merchantId, name, description, price]);
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
    ctx.body = 'Wares uploaded successfully';
  } catch (err) {
    ctx.throw(400, err.message);
  }
});

router.get('/wares', authMiddleware, async (ctx) => {
  const { minPrice, maxPrice } = ctx.query;
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

  const rows = await new Promise((resolve, reject) => {
    db.all(query, params, (err, rows) => {
      if (err) reject(err); else resolve(rows);
    });
  });

  let html = '<table><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>';
  rows.forEach(row => {
    html += `<tr><td>${row.name}</td><td>${row.price}</td><td>${row.description}</td><td>${row.email}</td></tr>`;
  });
  html += '</tbody></table>';

  ctx.type = 'text/html';
  ctx.body = html;
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});