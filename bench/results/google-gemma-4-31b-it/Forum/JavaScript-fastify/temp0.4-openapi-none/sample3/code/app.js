const fastify = require('fastify')({ logger: true });
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
        form { margin-bottom: 30px; padding: 20px; background: #f4f4f4; border-radius: 5px; }
        input, textarea { width: 100%; margin-bottom: 10px; display: block; padding: 8px; box-sizing: border-box; }
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
      <div id="messages">
        ${messageList || '<p>No messages yet.</p>'}
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
  const limitVal = parseInt(limit) || 10;
  const offsetVal = parseInt(offset) || 0;

  return new Promise((resolve, reject) => {
    db.all(
      `SELECT username, content, created_at FROM messages ORDER BY created_at ${sortDir} LIMIT ? OFFSET ?`,
      [limitVal, offsetVal],
      (err, rows) => {
        if (err) {
          reply.status(500).send('Internal Server Error');
          return reject(err);
        }
        reply.type('text/html').send(renderForum(rows));
        resolve();
      }
    );
  });
});

fastify.post('/messages', async (request, reply) => {
  const { username, content } = request.body;

  if (!username || !content) {
    return reply.status(400).send({ error: 'Invalid input: username and content are required' });
  }

  return new Promise((resolve, reject) => {
    db.run(
      `INSERT INTO messages (username, content) VALUES (?, ?)`,
      [username, content],
      function(err) {
        if (err) {
          reply.status(500).send({ error: 'Database error' });
          return reject(err);
        }
        reply.status(200).send({ status: 'Successful operation' });
        resolve();
      }
    );
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();