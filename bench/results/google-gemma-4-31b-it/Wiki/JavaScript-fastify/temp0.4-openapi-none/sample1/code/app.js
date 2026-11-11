const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    lastModifiedBy TEXT,
    lastModifiedAt TEXT
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS edits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entryId TEXT,
    content TEXT,
    modifiedBy TEXT,
    summary TEXT,
    modifiedAt TEXT,
    FOREIGN KEY(entryId) REFERENCES entries(id)
  )`);
});

// Helper to wrap db.get/all in promises
const dbGet = (query, params) => new Promise((res, rej) => {
  db.get(query, params, (err, row) => err ? rej(err) : res(row));
});
const dbAll = (query, params) => new Promise((res, rej) => {
  db.all(query, params, (err, rows) => err ? rej(err) : res(rows));
});
const dbRun = (query, params) => new Promise((res, rej) => {
  db.run(query, params, function(err) { err ? rej(err) : res(this); });
});

// Basic HTML Templates
const layout = (title, body) => `
  <!DOCTYPE html>
  <html>
  <head>
    <title>${title} - Wiki</title>
    <style>
      body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
      nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
      .entry-card { border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px; }
      .diff { background: #f4f4f4; padding: 10px; white-space: pre-wrap; border-left: 4px solid #ccc; }
      form { display: flex; flex-direction: column; gap: 10px; }
      textarea { height: 200px; }
      input, textarea { padding: 8px; }
    </style>
  </head>
  <body>
    <nav><a href="/entries">🏠 Home</a> | <a href="/entries/new">➕ New Entry</a></nav>
    <h1>${title}</h1>
    ${body}
  </body>
  </html>
`;

// Routes
fastify.get('/entries', async (request, reply) => {
  const rows = await dbAll('SELECT id, title FROM entries');
  const list = rows.map(row => `<li><a href="/entries/${row.id}">${row.title}</a></li>`).join('');
  reply.type('text/html').send(layout('Wiki Entries', `<ul>${list || 'No entries yet.'}</ul>`));
});

// Helper route for the "New Entry" UI (not explicitly in OpenAPI but needed for the app to be usable)
fastify.get('/entries/new', async (request, reply) => {
  const form = `
    <form action="/entries" method="POST">
      <input name="title" placeholder="Title" required />
      <input name="createdBy" placeholder="Your Name" required />
      <textarea name="content" placeholder="Content..." required></textarea>
      <button type="submit">Create Entry</button>
    </form>
  `;
  reply.type('text/html').send(layout('Create New Entry', form));
});

// Handle both JSON and Form submissions for POST /entries
fastify.post('/entries', async (request, reply) => {
  let data;
  if (request.headers['content-type'] === 'application/json') {
    data = request.body;
  } else {
    // Simple manual parse for application/x-www-form-urlencoded if multipart isn't used
    const params = new URLSearchParams(request.payload || '');
    data = {
      title: params.get('title'),
      content: params.get('content'),
      createdBy: params.get('createdBy')
    };
  }

  const id = uuidv4();
  const now = new Date().toISOString();
  
  await dbRun('INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [id, data.title, data.content, data.createdBy, now]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [id, data.content, data.createdBy, 'Initial creation', now]);

  reply.code(201).send({ id, ...data, lastModifiedAt: now });
});

fastify.get('/entries/:entryId', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  
  if (!entry) return reply.code(404).send('Entry not found');

  const body = `
    <div class="entry-card">
      <p>${entry.content}</p>
      <hr>
      <small>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</small>
      <div style="margin-top: 10px;">
        <a href="/entries/${entryId}/edit">✏️ Edit this page</a> | 
        <a href="/entries/${entryId}/edits">📜 History</a>
      </div>
    </div>
  `;
  reply.type('text/html').send(layout(entry.title, body));
});

// Helper route for the "Edit" UI
fastify.get('/entries/:entryId/edit', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

  const form = `
    <form action="/entries/${entryId}" method="POST">
      <input type="hidden" name="_method" value="PUT">
      <input name="modifiedBy" placeholder="Your Name" required />
      <input name="summary" placeholder="What did you change?" required />
      <textarea name="content" required>${entry.content}</textarea>
      <button type="submit">Save Changes</button>
    </form>
  `;
  reply.type('text/html').send(layout(`Editing ${entry.title}`, form));
});

// Handle PUT via POST (common for HTML forms) or actual PUT
fastify.route({
  method: ['PUT', 'POST'],
  url: '/entries/:entryId',
  handler: async (request, reply) => {
    const { entryId } = request.params;
    let data;
    
    if (request.headers['content-type'] === 'application/json') {
      data = request.body;
    } else {
      const params = new URLSearchParams(request.payload || '');
      data = {
        content: params.get('content'),
        modifiedBy: params.get('modifiedBy'),
        summary: params.get('summary')
      };
    }

    const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
    if (!entry) return reply.code(404).send('Entry not found');

    const now = new Date().toISOString();
    await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
      [data.content, data.modifiedBy, now, entryId]);
    await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
      [entryId, data.content, data.modifiedBy, data.summary, now]);

    reply.send({ id: entryId, title: entry.title, ...data, lastModifiedAt: now });
  }
});

fastify.get('/entries/:entryId/edits', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

  const edits = await dbAll('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [entryId]);
  
  const history = edits.map((edit, index) => {
    const prevEdit = edits[index + 1];
    const diff = prevEdit ? `From: ${prevEdit.content}\nTo: ${edit.content}` : 'Initial version';
    return `
      <div class="entry-card">
        <strong>${edit.modifiedBy}</strong> (${edit.modifiedAt})<br>
        <em>${edit.summary}</em>
        <div class="diff">${diff}</div>
      </div>
    `;
  }).join('');

  reply.type('text/html').send(layout(`History: ${entry.title}`, history || 'No edits found.'));
});

// Start server
fastify.listen({ port: 5000, host: '0.0.0.0' }, (err, address) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log(`Server listening on ${address}`);
});