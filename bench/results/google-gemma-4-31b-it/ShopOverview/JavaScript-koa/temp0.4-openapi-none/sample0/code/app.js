require('dotenv').config();
const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const session = require('koa-session');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const sqlite3 = require('sqlite3').verbose();
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

// Session configuration
app.keys = [APP_SECRET];
app.use(session({
    key: 'merchant.session',
    maxAge: 86400000,
    httpOnly: true,
    signed: true
}, app));
app.use(bodyParser());

// Middleware to check authentication via cookie/session
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

// POST /merchants/register
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
        ctx.body = { message: 'Merchant registered successfully' };
    } catch (err) {
        ctx.throw(400, 'Email already exists');
    }
});

// POST /merchants/login
router.post('/merchants/login', async (ctx) => {
    const { email, password } = ctx.request.body;
    if (!email || !password) {
        ctx.throw(400, 'Email and password required');
    }

    const merchant = await new Promise((resolve) => {
        db.get('SELECT * FROM merchants WHERE email = ?', [email], (err, row) => {
            resolve(row);
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

// POST /merchants/upload-wares
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
                for (const line of lines) {
                    const [name, description, priceStr] = line.split(',').map(s => s.trim());
                    const price = parseFloat(priceStr);
                    if (!name || !description || isNaN(price)) {
                        errorOccurred = true;
                        break;
                    }
                    db.run('INSERT INTO wares (id, merchant_id, name, description, price) VALUES (?, ?, ?, ?, ?)', 
                        [uuidv4(), merchantId, name, description, price]);
                }
                if (errorOccurred) {
                    db.run('ROLLBACK', () => reject(new Error('Invalid CSV format')));
                } else {
                    db.run('COMMIT', (err) => err ? reject(err) : resolve());
                }
            });
        });
        ctx.body = { message: 'Wares uploaded successfully' };
    } catch (err) {
        ctx.throw(400, 'Invalid CSV format');
    }
});

// GET /wares
router.get('/wares', async (ctx) => {
    const minPrice = parseFloat(ctx.query.minPrice) || 0;
    const maxPrice = parseFloat(ctx.query.maxPrice) || Infinity;

    const rows = await new Promise((resolve) => {
        const query = `
            SELECT w.name, w.price, w.description, m.email 
            FROM wares w 
            JOIN merchants m ON w.merchant_id = m.id 
            WHERE w.price >= ? AND w.price <= ?`;
        db.all(query, [minPrice, maxPrice], (err, rows) => {
            resolve(rows || []);
        });
    });

    let html = '<html><body><h1>Offered Wares</h1><table border="1"><thead>';
    html += '<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>';
    
    rows.forEach(row => {
        html += `<tr><td>${row.name}</td><td>${row.price}</td><td>${row.description}</td><td>${row.email}</td></tr>`;
    });

    html += '</tbody></table></body></html>';
    ctx.type = 'text/html';
    ctx.body = html;
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});