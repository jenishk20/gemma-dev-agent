const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const dotenv = require('dotenv');

dotenv.config();

const app = express();
const port = 5000;
const db = new sqlite3.Database('db.sqlite3');

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Initialize Database
db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
});

// Helper to render a simple HTML page for the forum
function renderForum(messages) {
    const messageList = messages.map(m => `
        <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
            <strong>${m.username}</strong> <small style="color: gray;">${m.created_at}</small>
            <p>${m.content}</p>
        </div>
    `).join('');

    return `
        <!DOCTYPE html>
        <html>
        <head>
            <title>MyForum</title>
            <style>
                body { font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                form { margin-bottom: 30px; padding: 20px; background: #f9f9f9; border-radius: 5px; }
                input, textarea { display: block; width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
                button { padding: 10px 20px; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>MyForum</h1>
            <form action="/messages" method="POST">
                <input type="text" name="username" placeholder="Username" required>
                <textarea name="content" placeholder="Message content" required></textarea>
                <button type="submit">Post Message</button>
            </form>
            <hr>
            <h2>Messages</h2>
            ${messageList || '<p>No messages yet.</p>'}
        </body>
        </html>
    `;
}

// GET /messages
app.get('/messages', (req, res) => {
    const limit = parseInt(req.query.limit) || 10;
    const offset = parseInt(req.query.offset) || 0;
    const sort = (req.query.sort || 'DESC').toUpperCase();
    const order = sort === 'ASC' ? 'ASC' : 'DESC';

    const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${order} LIMIT ? OFFSET ?`;
    
    db.all(query, [limit, offset], (err, rows) => {
        if (err) {
            return res.status(500).send("Internal Server Error");
        }
        res.send(renderForum(rows));
    });
});

// POST /messages
app.post('/messages', (req, res) => {
    // Support both JSON and URL-encoded (from the HTML form)
    const { username, content } = req.body;

    if (!username || !content) {
        return res.status(400).send("Invalid input: username and content are required");
    }

    const query = `INSERT INTO messages (username, content) VALUES (?, ?)`;
    db.run(query, [username, content], function(err) {
        if (err) {
            return res.status(500).send("Internal Server Error");
        }
        res.status(200).send("Successful operation");
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`MyForum listening at http://0.0.0.0:${port}/messages`);
});