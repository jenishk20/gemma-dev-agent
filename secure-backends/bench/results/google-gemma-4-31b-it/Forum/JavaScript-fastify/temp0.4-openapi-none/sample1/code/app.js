const fastify = require('fastify')({ logger: false });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Initialize Database
const db = new sqlite3.Database('db.sqlite3');

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
        form { background: #f4f4f4; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        input, textarea { width: 100%; margin-bottom: 10px; display: block; }
        .nav { margin-bottom: 20px; }
      </style>
    </head>
    <body>
      <h1>MyForum</h1>
      <form action="/messages" method="POST">
        <input type="text" name="username" placeholder="Username" required>
        <textarea name="content" placeholder="Message content" required></textarea>
        <button type="submit">Post Message</button>
      </form>
      <div class="nav">
        <a href="/messages?sort=DESC">Newest First</a> | 
        <a href="/messages?sort=ASC">Oldest First</a>
      </div>
      <div id="messages">
        ${messageList || '<p>No messages yet!</p>'}
      </div>
    </body>
    </html>
  `;
};

// Routes
fastify.get('/messages', async (request, reply) => {
  const { limit = 10, offset = 0, sort = 'DESC' } = request.query;
  
  // Validate sort enum
  const sortDir = (sort.toUpperCase() === 'ASC') ? 'ASC' : 'DESC';
  const lim = parseInt(limit) || 10;
  const off = parseInt(offset) || 0;

  return new Promise((resolve, reject) => {
    const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${sortDir} LIMIT ? OFFSET ?`;
    db.all(query, [lim, off], (err, rows) => {
      if (err) {
        reply.status(500).send('Database Error');
        return reject(err);
      }
      reply.type('text/html').send(renderForum(rows));
      resolve();
    });
  });
});

// Handle both JSON (as per OpenAPI) and Form submission (for the HTML UI)
fastify.post('/messages', async (request, reply) => {
  let username, content;

  if (request.headers['content-type'] === 'application/json') {
    username = request.body.username;
    content = request.body.content;
  } else {
    // Since @fastify/multipart is allowed but not strictly required for simple forms, 
    // we handle the case where the user might use a standard HTML form.
    // However, the OpenAPI spec specifically asks for application/json.
    // To support the HTML form provided in the UI, we'd usually use multipart.
    // For this implementation, we'll prioritize the OpenAPI JSON spec.
    return reply.status(400).send('Please send application/json');
  }

  if (!username || !content) {
    return reply.status(400).send('Invalid input: username and content are required');
  }

  return new Promise((resolve, reject) => {
    db.run(`INSERT INTO messages (username, content) VALUES (?, ?)`, [username, content], function(err) {
      if (err) {
        reply.status(500).send('Database Error');
        return reject(err);
      }
      reply.status(200).send('Successful operation');
      resolve();
    });
  });
});

// Special route to handle the HTML form submission via a redirect or custom handler
// because standard HTML forms send application/x-www-form-urlencoded
fastify.addHook('onRequest', async (request, reply) => {
  // This is a shim to allow the HTML form in the UI to work while keeping the JSON API
  if (request.method === 'POST' && request.url === '/messages' && request.headers['content-type']?.includes('application/x-www-form-urlencoded')) {
    // We manually parse the body for the HTML form since we aren't using a form-body plugin
    let body = '';
    for await (const chunk of request.raw) {
      body += chunk;
    }
    const params = new URLSearchParams(body);
    const username = params.get('username');
    const content = params.get('content');

    if (username && content) {
      db.run(`INSERT INTO messages (username, content) VALUES (?, ?)`, [username, content]);
      reply.redirect('/messages');
      reply.send(); // End request
      return true; // stop further processing
    }
  }
});

// Start server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();