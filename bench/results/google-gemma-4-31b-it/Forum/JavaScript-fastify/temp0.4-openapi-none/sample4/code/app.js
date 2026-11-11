const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = fastify({ logger: true });
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
});

// HTML Template for the forum
const renderForum = (messages) => {
  const messageList = messages.map(m => `
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
      <style>
        body { font-family: sans-serif; max-width: 600px; margin: 20px auto; padding: 0 20px; }
        form { margin-bottom: 30px; padding: 20px; background: #f4f4f4; border-radius: 5px; }
        input, textarea { display: block; width: 100%; margin-bottom: 10px; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; cursor: pointer; }
      </style>
    </head>
    <body>
      <h1>MyForum</h1>
      
      <form action="/messages" method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <textarea name="content" placeholder="Message content..." required></textarea>
        <button type="submit">Post Message</button>
      </form>

      <hr>
      <h2>Messages</h2>
      ${messageList || '<p>No messages yet.</p>'}
      
      <div style="margin-top: 20px;">
        <a href="/messages?sort=ASC">Oldest First</a> | 
        <a href="/messages?sort=DESC">Newest First</a>
      </div>
    </body>
    </html>
  `;
};

// GET /messages
app.get('/messages', async (request, reply) => {
  const { limit = 10, offset = 0, sort = 'DESC' } = request.query;
  
  const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${sort.toUpperCase()} LIMIT ? OFFSET ?`;
  
  return new Promise((resolve, reject) => {
    db.all(query, [limit, offset], (err, rows) => {
      if (err) {
        reply.status(500).send('Internal Server Error');
        return reject(err);
      }
      reply.type('text/html').send(renderForum(rows));
      resolve();
    });
  });
});

// POST /messages (JSON API)
app.post('/messages', async (request, reply) => {
  const { username, content } = request.body;

  if (!username || !content) {
    return reply.status(400).send({ error: 'Invalid input: username and content are required' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT INTO messages (username, content) VALUES (?, ?)');
    stmt.run(username, content, function(err) {
      if (err) {
        reply.status(500).send({ error: 'Database error' });
        return reject(err);
      }
      reply.status(200).send({ status: 'Successful operation' });
      resolve();
    });
  });
});

// Handle form submission (HTML redirect)
// Since the OpenAPI specifies JSON for POST, but the UI needs a way to post, 
// we handle the form data by checking the content type or adding a specific route.
// To strictly follow OpenAPI while supporting the HTML UI, we can add a middleware 
// or just use the JSON endpoint via JS, but for simplicity in a single file, 
// let's add a handler for urlencoded data if it comes from the HTML form.
app.addHook('preprocess', async (request, reply) => {
  if (request.method === 'POST' && request.headers['content-type'] === 'application/x-www-form-urlencoded') {
    // Manual parsing of form data for the HTML form
    const body = request.body;
    if (typeof body === 'string') {
      const params = new URLSearchParams(body);
      request.body = {
        username: params.get('username'),
        content: params.get('content')
      };
    }
  }
});

// Override POST /messages to handle both JSON and Form, then redirect back to home
app.post('/messages', async (request, reply) => {
  const { username, content } = request.body;

  if (!username || !content) {
    return reply.status(400).send({ error: 'Invalid input' });
  }

  return new Promise((resolve) => {
    db.run('INSERT INTO messages (username, content) VALUES (?, ?)', [username, content], function(err) {
      if (err) {
        reply.status(500).send({ error: 'Database error' });
        return resolve();
      }
      
      // If it was a form submission, redirect to GET /messages
      if (request.headers['content-type'] === 'application/x-www-form-urlencoded') {
        reply.redirect('/messages');
      } else {
        reply.status(200).send({ status: 'Successful operation' });
      }
      resolve();
    });
  });
});

// Start server
app.listen({ port: 5000, host: '0.0.0.0' }, (err) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log('Server listening on http://0.0.0.0:5000');
});