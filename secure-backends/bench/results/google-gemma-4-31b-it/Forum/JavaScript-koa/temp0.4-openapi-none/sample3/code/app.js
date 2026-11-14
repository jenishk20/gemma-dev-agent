const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
});

// HTML Template Helper
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
            body { font-family: sans-serif; max-width: 600px; margin: 20px auto; padding: 0 20px; }
            form { margin-bottom: 30px; padding: 15px; background: #f4f4f4; border-radius: 5px; }
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
router.get('/messages', async (ctx) => {
    const limit = parseInt(ctx.query.limit) || 10;
    const offset = parseInt(ctx.query.offset) || 0;
    const sort = (ctx.query.sort || 'DESC').toUpperCase();
    const order = sort === 'ASC' ? 'ASC' : 'DESC';

    const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${order} LIMIT ? OFFSET ?`;
    
    db.all(query, [limit, offset], (err, rows) => {
        if (err) {
            ctx.throw(500, 'Database error');
        }
        ctx.type = 'text/html';
        ctx.body = renderForum(rows);
    });
});

// POST /messages
// Note: The OpenAPI schema specifies application/json, but for a forum webapp 
// we typically handle both JSON and Form data. We'll prioritize JSON as per schema.
router.post('/messages', async (ctx) => {
    const { username, content } = ctx.request.body;

    if (!username || !content) {
        ctx.status = 400;
        ctx.body = 'Invalid input: username and content are required';
        return;
    }

    const query = `INSERT INTO messages (username, content) VALUES (?, ?)`;
    db.run(query, [username, content], function(err) {
        if (err) {
            ctx.status = 500;
            ctx.body = 'Database error';
            return;
        }
        ctx.status = 200;
        ctx.body = 'Successful operation';
    });
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
    console.log('Server running on http://0.0.0.0:5000');
});