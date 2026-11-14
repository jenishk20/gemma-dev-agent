const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
app.use(express.json());

const PORT = 5000;
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key';

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
    )`);
    db.run(`CREATE TABLE IF NOT EXISTS secrets (
        username TEXT PRIMARY KEY,
        secret_value TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    )`);
});

// Middleware for JWT authentication
const authenticateToken = (req, res, next) => {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];

    if (!token) {
        return res.status(401).json({ message: 'Invalid authentication token' });
    }

    jwt.verify(token, APP_SECRET, (err, user) => {
        if (err) return res.status(401).json({ message: 'Invalid authentication token' });
        req.user = user;
        next();
    });
};

// POST /register
app.post('/register', async (req, res) => {
    const { email, username, password } = req.body;

    if (!email || !username || !password) {
        return res.status(400).json({ message: 'Email, username, and password are required' });
    }

    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        const query = `INSERT INTO users (username, email, password) VALUES (?, ?, ?)`;
        
        db.run(query, [username, email, hashedPassword], function(err) {
            if (err) {
                if (err.message.includes('UNIQUE constraint failed')) {
                    return res.status(400).json({ message: 'Email already in use or invalid data' });
                }
                return res.status(500).json({ message: 'Internal server error' });
            }
            res.status(201).json({ message: 'Registration successful' });
        });
    } catch (error) {
        res.status(500).json({ message: 'Internal server error' });
    }
});

// POST /login
app.post('/login', (req, res) => {
    const { email, password } = req.body;

    if (!email || !password) {
        return res.status(400).json({ message: 'Email and password are required' });
    }

    const query = `SELECT * FROM users WHERE email = ?`;
    db.get(query, [email], async (err, user) => {
        if (err || !user) {
            return res.status(401).json({ message: 'Invalid email or password' });
        }

        const match = await bcrypt.compare(password, user.password);
        if (!match) {
            return res.status(401).json({ message: 'Invalid email or password' });
        }

        const token = jwt.sign({ username: user.username, email: user.email }, APP_SECRET, { expiresIn: '1h' });
        res.status(200).json({ token, message: 'Login successful' });
    });
});

// POST /set_secret
app.post('/set_secret', authenticateToken, (req, res) => {
    const { username, secret } = req.body;

    if (!username || secret === undefined) {
        return res.status(400).json({ message: 'Username and secret are required' });
    }

    // Ensure the token belongs to the user trying to set the secret
    if (req.user.username !== username) {
        return res.status(401).json({ message: 'Invalid authentication token' });
    }

    const query = `INSERT INTO secrets (username, secret_value) VALUES (?, ?) 
                   ON CONFLICT(username) DO UPDATE SET secret_value = excluded.secret_value`;
    
    db.run(query, [username, secret], function(err) {
        if (err) {
            return res.status(500).json({ message: 'Internal server error' });
        }
        res.status(200).json({ message: 'Secret has been set successfully' });
    });
});

// GET /get_secret
app.get('/get_secret', authenticateToken, (req, res) => {
    const { username } = req.query;

    if (!username) {
        return res.status(400).json({ message: 'Username query parameter is required' });
    }

    // Ensure the token belongs to the user trying to retrieve the secret
    if (req.user.username !== username) {
        return res.status(401).json({ message: 'Invalid authentication token' });
    }

    const query = `SELECT secret_value FROM secrets WHERE username = ?`;
    db.get(query, [username], (err, row) => {
        if (err) {
            return res.status(500).json({ message: 'Internal server error' });
        }
        if (!row) {
            return res.status(404).json({ message: 'Secret not found' });
        }
        res.status(200).json({ secret: row.secret_value });
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
});