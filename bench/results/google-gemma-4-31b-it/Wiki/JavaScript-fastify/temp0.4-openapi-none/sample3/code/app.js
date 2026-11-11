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

// Simple HTML Templates
const layout = (title, content) => `
  <!DOCTYPE html>
  <html>
  <head>
    <title>${title} - Wiki</title>
    <style>
      body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
      nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
      .entry-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
      .diff { background: #f4f4f4; padding: 10px; border-left: 4px solid #ccc; margin: 10px 0; white-space: pre-wrap; }
      form { display: flex; flex-direction: column; gap: 10px; max-width: 400px; }
      textarea { height: 200px; }
    </style>
  </head>
  <body>
    <nav><a href="/entries">🏠 Home</a> | <a href="/entries/new">➕ New Entry</a></nav>
    <h1>${title}</h1>
    ${content}
  </body>
  </html>
`;

// Routes
fastify.get('/entries', async (request, reply) => {
  const rows = await dbAll('SELECT id, title FROM entries');
  let listHtml = '<ul>';
  rows.forEach(row => {
    listHtml += `<li><a href="/entries/${row.id}">${row.title}</a></li>`;
  });
  listHtml += '</ul>';
  
  reply.type('text/html').send(layout('Wiki Entries', listHtml));
});

// Custom route for the "New Entry" form (not explicitly in OpenAPI but needed for the POST)
fastify.get('/entries/new', async (request, reply) => {
  const form = `
    <form method="POST" action="/entries">
      <input name="title" placeholder="Title" required /><br/>
      <input name="createdBy" placeholder="Your Name" required /><br/>
      <textarea name="content" placeholder="Content" required></textarea><br/>
      <button type="submit">Create Entry</button>
    </form>
  `;
  reply.type('text/html').send(layout('Create New Entry', form));
});

fastify.post('/entries', async (request, reply) => {
  // Support both JSON and Form Data for convenience
  let body = request.body;
  if (request.headers['content-type'] === 'application/x-www-form-urlencoded') {
    // Simple parser for form data since we can't use extra plugins not listed
    const params = new URLSearchParams(request.body);
    body = {
      title: params.get('title'),
      content: params.get('content'),
      createdBy: params.get('createdBy')
    };
  }

  const { title, content, createdBy } = body;
  const id = uuidv4();
  const now = new Date().toISOString();

  await dbRun('INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [id, title, content, createdBy, now]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [id, content, createdBy, 'Initial creation', now]);

  reply.code(201).send({ id, title, content, lastModifiedBy: createdBy, lastModifiedAt: now });
});

fastify.get('/entries/:entryId', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);

  if (!entry) return reply.code(404).send('Entry not found');

  const contributors = await dbAll('SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?', [entryId]);
  const contributorList = contributors.map(c => c.modifiedBy).join(', ');

  const contentHtml = `
    <div class="entry-box">
      <p>${entry.content}</p>
      <hr/>
      <small>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</small><br/>
      <small>Contributors: ${contributorList}</small><br/>
      <a href="/entries/${entryId}/edit">📝 Edit this page</a> | 
      <a href="/entries/${entryId}/edits">📜 History</a>
    </div>
  `;
  reply.type('text/html').send(layout(entry.title, contentHtml));
});

// Custom route for the Edit form
fastify.get('/entries/:entryId/edit', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

  const form = `
    <form method="PUT" action="/entries/${entryId}">
      <input name="modifiedBy" placeholder="Your Name" required /><br/>
      <input name="summary" placeholder="Edit Summary (e.g. Fixed typo)" required /><br/>
      <textarea name="content" required>${entry.content}</textarea><br/>
      <button type="submit">Save Changes</button>
    </form>
    <p>Note: Browser HTML forms only support GET/POST. This endpoint expects PUT via API or a JS wrapper.</p>
    <script>
      document.querySelector('form').onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        const res = await fetch(e.target.action, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        if (res.ok) window.location.href = '/entries/${entryId}';
        else alert('Error updating entry');
      };
    </script>
  `;
  reply.type('text/html').send(layout(`Editing ${entry.title}`, form));
});

fastify.put('/entries/:entryId', async (request, reply) => {
  const { entryId } = request.params;
  const { content, modifiedBy, summary } = request.body;
  const now = new Date().toISOString();

  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send({ error: 'Entry not found' });

  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
    [content, modifiedBy, now, entryId]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [entryId, content, modifiedBy, summary, now]);

  reply.send({ 
    id: entryId, 
    title: entry.title, 
    content, 
    lastModifiedBy: modifiedBy, 
    lastModifiedAt: now 
  });
});

fastify.get('/entries/:entryId/edits', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

  const edits = await dbAll('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [entryId]);
  
  let historyHtml = '<h3>Edit History</h3>';
  edits.forEach((edit, index) => {
    historyHtml += `
      <div class="entry-box" style="margin-bottom: 10px;">
        <strong>${edit.modifiedBy}</strong> - ${edit.modifiedAt}<br/>
        <em>Summary: ${edit.summary}</em>
        <div class="diff">${edit.content}</div>
      </div>
    `;
  });

  reply.type('text/html').send(layout(`History: ${entry.title}`, historyHtml));
});

// Start Server
fastify.listen({ host: '0.0.0.0', port: 5000 }, (err) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log('Wiki server running at http://0.0.0.0:5000');
});