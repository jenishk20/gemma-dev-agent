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

// Helper to render a simple HTML page for the forum
function renderForum(messages) {
  const messageItems = messages.map(m => `
    <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
      <strong>${m.username}</strong> <small>${m.created_at}</small><br>
      <p>${m.content}</p>
    </div>
  `).join('');

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>MyForum</title>
      <style>body { font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }</style>
    </head>
    <body>
      <h1>MyForum</h1>
      <div style="margin-bottom: 30px; padding: 15px; background: #f4f4f4; border-radius: 5px;">
        <h3>Post a Message</h3>
        <form action="/messages" method="POST" id="postForm">
          <input type="text" name="username" placeholder="Username" required style="display:block; margin-bottom:10px; width:100%"><br>
          <textarea name="content" placeholder="Message" required style="display:block; margin-bottom:10px; width:100%"></textarea><br>
          <button type="submit" id="submitBtn">Post</button>
        </form>
        <p id="msgStatus"></p>
      </div>
      <div id="messages">
        ${messageItems || '<p>No messages yet!</p>'}
      </div>
      <script>
        // Intercept form to send JSON as per OpenAPI spec
        document.getElementById('postForm').onsubmit = async (e) => {
          e.preventDefault();
          const formData = new FormData(e.target);
          const data = {
            username: formData.get('username'),
            content: formData.get('content')
          };
          const res = await fetch('/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
          });
          if (res.ok) {
            window.location.reload();
          } else {
            document.getElementById('msgStatus').innerText = 'Error posting message';
          }
        };
      </script>
    </body>
    </html>
  `;
}

// GET /messages
router.get('/messages', async (ctx) => {
  const limit = parseInt(ctx.query.limit) || 10;
  const offset = parseInt(ctx.query.offset) || 0;
  const sort = (ctx.query.sort || 'DESC').toUpperCase();
  
  const orderDir = (sort === 'ASC') ? 'ASC' : 'DESC';

  const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${orderDir} LIMIT ? OFFSET ?`;
  
  db.all(query, [limit, offset], (err, rows) => {
    if (err) {
      ctx.status = 500;
      ctx.body = 'Internal Server Error';
      return;
    }
    ctx.type = 'text/html';
    ctx.body = renderForum(rows);
  });
});

// POST /messages
router.post('/messages', async (ctx) => {
  const { username, content } = ctx.request.body;

  if (!username || !content) {
    ctx.status = 400;
    ctx.body = { error: 'Invalid input: username and content are required' };
    return;
  }

  const query = `INSERT INTO messages (username, content) VALUES (?, ?)`;
  db.run(query, [username, content], function(err) {
    if (err) {
      ctx.status = 500;
      ctx.body = { error: 'Database error' };
      return;
    }
    ctx.status = 200;
    ctx.body = { message: 'Successful operation' };
  });
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});