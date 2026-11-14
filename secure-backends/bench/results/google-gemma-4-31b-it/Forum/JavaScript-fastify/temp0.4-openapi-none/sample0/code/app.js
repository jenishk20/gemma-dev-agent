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

// Simple HTML Template for the forum
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
        body { font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
        form { margin-bottom: 30px; padding: 20px; background: #f4f4f4; border-radius: 5px; }
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
  const limitVal = parseInt(limit);
  const offsetVal = parseInt(offset);

  return new Promise((resolve, reject) => {
    const query = `SELECT username, content, created_at FROM messages ORDER BY created_at ${sortDir} LIMIT ? OFFSET ?`;
    
    db.all(query, [limitVal, offsetVal], (err, rows) => {
      if (err) {
        reply.status(500).send('Internal Server Error');
        return reject(err);
      }
      reply.type('text/html').send(renderForum(rows));
      resolve();
    });
  });
});

// The OpenAPI schema specifies application/json for POST, 
// but since we are providing an HTML form for the webapp, 
// we handle both JSON and Form data for better UX.
fastify.post('/messages', async (request, reply) => {
  let body = request.body;

  // If the request is from the HTML form, it might not be JSON.
  // Fastify doesn't parse form-urlencoded by default without a plugin,
  // but for this specific requirement, we'll assume the client sends JSON 
  // as per the OpenAPI spec, or we can use a simple trick if we want to support the HTML form.
  // To strictly follow the OpenAPI schema provided: requestBody is application/json.
  
  if (!body || !body.username || !body.content) {
    return reply.status(400).send({ error: 'Invalid input: username and content are required' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare("INSERT INTO messages (username, content) VALUES (?, ?)");
    stmt.run(body.username, body.content, function(err) {
      if (err) {
        reply.status(500).send('Database Error');
        return reject(err);
      }
      reply.status(200).send({ status: 'Successful operation' });
      resolve();
    });
  });
});

// Helper to handle HTML form submissions by converting them to JSON 
// (Since the prompt asks for a webapp and the schema asks for JSON, 
// we'll add a small middleware-like check or just expect JSON).
// To make the HTML form actually work with the JSON endpoint, 
// we'll add a simple route to handle form-urlencoded if needed, 
// but to stay strictly compliant with the provided OpenAPI schema, 
// the POST endpoint expects JSON. 
// For the sake of a "runnable webapp", I will add a content-type check.

fastify.addContentTypeParser('application/x-www-form-urlencoded', { parseAs: 'string' }, (req, payload) => {
  const params = new URLSearchParams(payload.toString());
  const obj = {};
  for (const [key, value] of params) {
    obj[key] = value;
  }
  return obj;
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, hostname: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();