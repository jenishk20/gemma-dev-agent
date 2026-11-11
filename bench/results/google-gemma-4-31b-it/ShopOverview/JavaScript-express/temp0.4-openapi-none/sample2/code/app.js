const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const cookieParser = require('cookie-parser');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
const PORT = 5000;
const SECRET = process.env.APP_SECRET || 'default_secret_key';

app.use(express.json());
app.use(cookieParser());

// Database Initialization
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

// Middleware for Cookie Authentication
const authenticate = (req, res, next) => {
    const token = req.cookies.AUTH_COOKIE;
    if (!token) return res.status(401).json({ error: 'Unauthorized' });

    jwt.verify(token, SECRET, (err, decoded) => {
        if (err) return res.status(401).json({ error: 'Unauthorized' });
        req.merchantId = decoded.id;
        next();
    });
};

// POST /merchants/register
app.post('/merchants/register', async (req, res) => {
    const { email, name, password } = req.body;
    if (!email || !name || !password) return res.status(400).send('Invalid input');

    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        const id = require('uuid').v4();
        
        const stmt = db.prepare("INSERT INTO merchants (id, email, name, password) VALUES (?, ?, ?, ?)");
        stmt.run(id, email, name, hashedPassword, (err) => {
            if (err) return res.status(400).send('Email already exists');
            res.status(201).send('Merchant registered successfully');
        });
        stmt.finalize();
    } catch (e) {
        res.status(500).send('Server error');
    }
});

// POST /merchants/login
app.post('/merchants/login', async (req, res) => {
    const { email, password } = req.body;
    if (!email || !password) return res.status(400).json({ error: 'Invalid input' });

    db.get("SELECT * FROM merchants WHERE email = ?", [email], async (err, merchant) => {
        if (err || !merchant) return res.status(401).json({ error: 'Invalid email or password' });

        const match = await bcrypt.compare(password, merchant.password);
        if (!match) return res.status(401).json({ error: 'Invalid email or password' });

        const token = jwt.sign({ id: merchant.id, email: merchant.email }, SECRET, { expiresIn: '1h' });
        res.cookie('AUTH_COOKIE', token, { httpOnly: true });
        res.status(200).json('Login successful');
    });
});

// POST /merchants/upload-wares
app.post('/merchants/upload-wares', authenticate, (req, res) => {
    const { csv } = req.body;
    if (!csv) return res.status(400).send('CSV data is required');

    const lines = csv.split('\n').filter(line => line.trim() !== '');
    const merchantId = req.merchantId;

    const stmt = db.prepare("INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)");
    
    let errorOccurred = false;
    let processedCount = 0;

    lines.forEach(line => {
        const [name, description, priceStr] = line.split(',');
        const price = parseFloat(priceStr);

        if (!name || !description || isNaN(price)) {
            errorOccurred = true;
        } else {
            stmt.run(merchantId, name.trim(), description.trim(), price);
            processedCount++;
        }
    });

    stmt.finalize();

    if (errorOccurred) {
        return res.status(400).send('Invalid CSV format');
    }
    res.status(200).send('Wares uploaded successfully');
});

// GET /wares
app.get('/wares', authenticate, (req, res) => {
    const minPrice = parseFloat(req.query.minPrice) || 0;
    const maxPrice = parseFloat(req.query.maxPrice) || Infinity;

    const query = `
        SELECT w.name, w.price, w.description, m.email 
        FROM wares w 
        JOIN merchants m ON w.merchant_id = m.id 
        WHERE w.price >= ? AND w.price <= ?
    `;

    db.all(query, [minPrice, maxPrice], (err, rows) => {
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

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
});