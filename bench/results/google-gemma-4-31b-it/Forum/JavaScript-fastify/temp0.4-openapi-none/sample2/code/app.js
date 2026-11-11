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

// Simple HTML template for the forum
const renderForum = (messages) => {
  const messageList = messages.map(m => `
    <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
      <strong>${m.username}</strong> <small style="color: gray;">${m.created_at}</small><br>
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
        form { margin-bottom: 30px; padding: 15px; background: #f4f4f4; border-radius: 5px; }
        input, textarea { width: 100%; margin-bottom: 10px; display: block; }
        button { cursor: pointer; padding: 10px 20px; }
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
      <div id="messages">
        ${messageList || '<p>No messages yet!</p>'}
      </div>
    </body>
    </html>
  `;
};

// Route: GET /messages
fastify.get('/messages', async (request, reply) => {
  const { limit = 10, offset = 0, sort = 'DESC' } = request.query;
  
  // Validate sort enum
  const direction = sort.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';
  const limitVal = parseInt(limit) || 10;
  const offsetVal = parseInt(offset) || 0;

  return new Promise((resolve, reject) => {
    const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${direction} LIMIT ? OFFSET ?`;
    db.all(query, [limitVal, offsetVal], (err, rows) => {
      if (err) {
        reply.status(500).send('Database Error');
        return reject(err);
      }
      const html = renderForum(rows);
      reply.type('text/html').send(html);
      resolve();
    });
  });
});

// Route: POST /messages
// The OpenAPI spec asks for application/json, but for a webapp we handle both 
// JSON and form-urlencoded to make the HTML form work.
fastify.post('/messages', async (request, reply) => {
  let username, content;

  if (request.headers['content-type']?.includes('application/json')) {
    username = request.body.username;
    content = request.body.content;
  } else {
    // Simple manual parsing for application/x-www-form-urlencoded since we can't use extra plugins
    // Fastify doesn't parse form-urlencoded by default without @fastify/formbody
    // However, we can use a simple trick or just expect JSON as per strict OpenAPI.
    // To support the HTML form provided in renderForum, we'll handle the raw body if needed.
    // But since the prompt asks to correspond to the OpenAPI schema (which specifies JSON),
    // we will prioritize JSON. For the sake of a "webapp", we'll add a small helper.
    return reply.status(400).send('Please send request as application/json');
  }

  if (!username || !content) {
    return reply.status(400).send('Invalid input: username and content are required');
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare("INSERT INTO messages (username, content) VALUES (?, ?)");
    stmt.run(username, content, function (err) {
      if (err) {
        reply.status(500).send('Database Error');
        return reject(err);
      }
      reply.status(200).send('Successful operation');
      resolve();
    });
    stmt.finalize();
  });
});

// Special handler for the HTML form to allow it to work via JSON (via a small client-side script)
// Since I must put everything in one file and follow the OpenAPI (JSON POST), 
// I will modify the renderForum to use JS to send JSON.
const renderForumWithJS = (messages) => {
  const messageList = messages.map(m => `
    <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
      <strong>${m.username}</strong> <small style="color: gray;">${m.created_at}</small><br>
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
        form { margin-bottom: 30px; padding: 15px; background: #f4f4f4; border-radius: 5px; }
        input, textarea { width: 100%; margin-bottom: 10px; display: block; box-sizing: border-box; }
        button { cursor: pointer; padding: 10px 20px; }
      </style>
    </head>
    <body>
      <h1>MyForum</h1>
      <form id="forumForm">
        <input type="text" id="username" placeholder="Username" required>
        <textarea id="content" placeholder="Message content" required></textarea>
        <button type="submit">Post Message</button>
      </form>
      <hr>
      <div id="messages">
        ${messageList || '<p>No messages yet!</p>'}
      </div>
      <script>
        document.getElementById('forumForm').onsubmit = async (e) => {
          e.preventDefault();
          const username = document.getElementById('username').value;
          const content = document.getElementById('content').value;
          const res = await fetch('/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, content })
          });
          if (res.ok) {
            window.location.reload();
          } else {
            alert('Error posting message');
          }
        };
      </script>
    </body>
    </html>
  `;
};

// Override the GET handler to use the JS version
fastify.get('/messages', async (request, reply) => {
  const { limit = 10, offset = 0, sort = 'DESC' } = request.query;
  const direction = sort.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';
  const limitVal = parseInt(limit) || 10;
  const offsetVal = parseInt(offset) || 0;

  return new Promise((resolve, reject) => {
    const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${direction} LIMIT ? OFFSET ?`;
    db.all(query, [limitVal, offsetVal], (err, rows) => {
      if (err) {
        reply.status(500).send('Database Error');
        return reject(err);
      }
      reply.type('text/html').send(renderForumWithJS(rows));
      resolve();
    });
  });
});

// Start Server
fastify.listen({ port: 5000, host: '0.0.0.0' }, (err) => {
  if (err) {
    process.exit(1);
  }
  console.log('Server is running on http://0.0.0.0:5000');
});