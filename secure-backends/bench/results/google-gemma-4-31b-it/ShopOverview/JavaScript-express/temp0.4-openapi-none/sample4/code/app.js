require('dotenv').config();
const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const cookieParser = require('cookie-parser');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key';

app.use(express.json());
app.use(cookieParser());

// Database initialization
const db = new sqlite3.Database('./db.sqlite3');

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

// Middleware for cookie authentication
const authenticate = (req, res, next) => {
    const token = req.cookies.AUTH_COOKIE;
    if (!token) return res.status(401).json({ error: 'Unauthorized' });

    try {
        const decoded = jwt.verify(token, APP_SECRET);
        req.merchantId = decoded.id;
        next();
    } catch (err) {
        return res.status(401).json({ error: 'Invalid token' });
    }
};

// POST /merchants/register
app.post('/merchants/register', async (req, res) => {
    const { email, name, password } = req.body;
    if (!email || !name || !password) {
        return res.status(400).json({ error: 'Invalid input' });
    }

    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        const id = uuidv4();
        db.run('INSERT INTO merchants (id, email, name, password) VALUES (?, ?, ?, ?)', 
            [id, email, name, hashedPassword], 
            function(err) {
                if (err) return res.status(400).json({ error: 'Email already exists' });
                res.status(201).send('Merchant registered successfully');
            }
        );
    } catch (e) {
        res.status(500).send('Server error');
    }
});

// POST /merchants/login
app.post('/merchants/login', async (req, res) => {
    const { email, password } = req.body;
    if (!email || !password) return res.status(400).json({ error: 'Invalid input' });

    db.get('SELECT * FROM merchants WHERE email = ?', [email], async (err, merchant) => {
        if (err || !merchant) return res.status(401).json({ error: 'Invalid email or password' });

        const match = await bcrypt.compare(password, merchant.password);
        if (!match) return res.status(401).json({ error: 'Invalid email or password' });

        const token = jwt.sign({ id: merchant.id, email: merchant.email }, APP_SECRET, { expiresIn: '1h' });
        res.cookie('AUTH_COOKIE', token, { httpOnly: true });
        res.status(200).json('Login successful');
    });
});

// POST /merchants/upload-wares
app.post('/merchants/upload-wares', authenticate, (req, res) => {
    const { csv } = req.body;
    if (!csv) return res.status(400).json({ error: 'CSV content is required' });

    const lines = csv.split('\n').filter(line => line.trim() !== '');
    const waresToInsert = [];

    for (let line of lines) {
        const [name, description, priceStr] = line.split(',').map(s => s.trim());
        const price = parseFloat(priceStr);
        if (!name || !description || isNaN(price)) {
            return res.status(400).json({ error: 'Invalid CSV format' });
        }
        waresToInsert.push([uuidv4(), req.merchantId, name, description, price]);
    }

    db.serialize(() => {
        db.run('BEGIN TRANSACTION');
        const stmt = db.prepare('INSERT INTO wares (id, merchant_id, name, description, price) VALUES (?, ?, ?, ?, ?)');
        waresToInsert.forEach(ware => stmt.run(ware));
        stmt.finalize();
        db.run('COMMIT', (err) => {
            if (err) return res.status(500).send('Database error');
            res.status(200).send('Wares uploaded successfully');
        });
    });
});

// GET /wares
app.get('/wares', authenticate, (req, res) => {
    const { minPrice, maxPrice } = req.query;
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

    db.all(query, params, (err, rows) => {
        if (err) return res.status(500).send('Database error');

        let html = '<html><body><h1>Offered Wares</h1><table border="1"><thead>';
        html += '<tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant Email</th></tr></thead><tbody>';
        
        rows.forEach(row => {
            html += `<tr><td>${row.name}</td><td>${row.price}</td><td>${row.description}</td><td>${row.email}</td></tr>`;
        });

        html += '</tbody></table></body></html>';
        res.setHeader('Content-Type', 'text/html');
        res.status(200).send(html);
    });
});

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}`);
});