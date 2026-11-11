const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = 5000;
const HOST = '0.0.0.0';
const APP_SECRET = process.env.APP_SECRET || 'default_secret_key_change_me';

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Database Setup
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL
    )`);
});

// --- API Routes ---

// Registration Endpoint
app.post('/register', async (req, res) => {
    const { email, password, name } = req.body;

    if (!email || !password || !name) {
        return res.status(400).json({ message: 'Email, password, and name are required' });
    }

    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        
        const stmt = db.prepare('INSERT INTO users (email, password, name) VALUES (?, ?, ?)');
        stmt.run(email, hashedPassword, name, function(err) {
            if (err) {
                if (err.message.includes('UNIQUE constraint failed')) {
                    return res.status(400).json({ message: 'Email already in use' });
                }
                return res.status(500).json({ message: 'Internal server error' });
            }
            res.status(201).json({ message: 'Registration successful' });
        });
        stmt.finalize();
    } catch (error) {
        res.status(500).json({ message: 'Internal server error' });
    }
});

// Login Endpoint
app.post('/login', async (req, res) => {
    const { email, password } = req.body;

    if (!email || !password) {
        return res.status(400).json({ message: 'Email and password are required' });
    }

    db.get('SELECT * FROM users WHERE email = ?', [email], async (err, user) => {
        if (err) {
            return res.status(500).json({ message: 'Internal server error' });
        }
        if (!user) {
            return res.status(401).json({ message: 'Invalid email or password' });
        }

        const match = await bcrypt.compare(password, user.password);
        if (!match) {
            return res.status(401).json({ message: 'Invalid email or password' });
        }

        const token = jwt.sign({ userId: user.id, email: user.email }, APP_SECRET, { expiresIn: '1h' });
        res.status(200).json({
            token: token,
            message: 'Login successful'
        });
    });
});

// --- Frontend (Simple HTML) ---

app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login & Register</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center; gap: 50px; margin-top: 50px; }
                .form-box { border: 1px solid #ccc; padding: 20px; border-radius: 8px; width: 300px; }
                input { display: block; width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
                button { width: 100%; padding: 10px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 4px; }
                .msg { margin-top: 10px; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <div class="form-box">
                <h3>Login</h3>
                <form id="loginForm">
                    <input type="email" name="email" placeholder="Email" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                </form>
                <div id="loginMsg" class="msg"></div>
            </div>
            <div class="form-box">
                <h3>Register</h3>
                <form id="regForm">
                    <input type="text" name="name" placeholder="Full Name" required>
                    <input type="email" name="email" placeholder="Email" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Register</button>
                </form>
                <div id="regMsg" class="msg"></div>
            </div>

            <script>
                async function handleForm(e, endpoint, msgId) {
                    e.preventDefault();
                    const formData = new FormData(e.target);
                    const data = Object.fromEntries(formData.entries());
                    const res = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    const result = await res.json();
                    document.getElementById(msgId).innerText = result.message + (result.token ? ' Token: ' + result.token : '');
                    document.getElementById(msgId).style.color = res.ok ? 'green' : 'red';
                }

                document.getElementById('loginForm').onsubmit = (e) => handleForm(e, '/login', 'loginMsg');
                document.getElementById('regForm').onsubmit = (e) => handleForm(e, '/register', 'regMsg');
            </script>
        </body>
        </html>
    `);
});

app.listen(PORT, HOST, () => {
    console.log(`Server running at http://${HOST}:${PORT}`);
});