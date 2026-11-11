const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const port = 5000;

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Database Setup
const db = new sqlite3.Database('./db.sqlite3', (err) => {
    if (err) console.error('Error opening database', err);
});

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
    const messageItems = messages.map(m => `
        <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 5px;">
            <strong>${m.username}</strong> <small>${m.created_at}</small><br>
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
                form { margin-bottom: 30px; padding: 15px; background: #f9f9f9; border-radius: 5px; }
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
            ${messageItems || '<p>No messages yet.</p>'}
        </body>
        </html>
    `;
}

// GET /messages
app.get('/messages', (req, res) => {
    const limit = parseInt(req.query.limit) || 10;
    const offset = parseInt(req.query.offset) || 0;
    const sort = (req.query.sort || 'DESC').toUpperCase();
    
    const orderDir = sort === 'ASC' ? 'ASC' : 'DESC';
    const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${orderDir} LIMIT ? OFFSET ?`;

    db.all(query, [limit, offset], (err, rows) => {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }
        res.send(renderForum(rows));
    });
});

// POST /messages
app.post('/messages', (req, res) => {
    // The OpenAPI schema specifies application/json, but for a webapp we handle both
    let username, content;
    
    if (req.headers['content-type'] === 'application/json') {
        username = req.body.username;
        content = req.body.content;
    } else {
        username = req.body.username;
        content = req.body.content;
    }

    if (!username || !content) {
        return res.status(400).send('Invalid input: username and content are required');
    }

    const query = `INSERT INTO messages (username, content) VALUES (?, ?)`;
    db.run(query, [username, content], function(err) {
        if (err) {
            return res.status(500).send('Internal Server Error');
        }
        // According to OpenAPI, 200 OK for successful operation.
        // For a webapp experience, we redirect back to the list.
        if (req.headers['accept'] && req.headers['accept'].includes('text/html')) {
            res.redirect('/messages');
        } else {
            res.status(200).send('Message posted successfully');
        }
    });
});

app.listen(port, '0.0.0.0', () => {
    console.log(`MyForum server running at http://0.0.0.0:${port}`);
});