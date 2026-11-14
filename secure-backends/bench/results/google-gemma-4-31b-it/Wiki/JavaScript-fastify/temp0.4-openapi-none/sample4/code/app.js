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
        pre { background: #f4f4f4; padding: 10px; overflow: auto; }
        .diff-old { color: red; text-decoration: line-through; }
        .diff-new { color: green; }
      </style>
    </head>
    <body>
      <nav><a href="/entries">🏠 Home</a> | <a href="/entries/new">➕ New Entry</a></nav>
      ${content}
    </body>
  </html>
`;

// Routes
fastify.get('/entries', async (request, reply) => {
  const rows = await dbAll('SELECT id, title FROM entries');
  let listHtml = '<h1>Wiki Entries</h1><ul>';
  rows.forEach(row => {
    listHtml += `<li><a href="/entries/${row.id}">${row.title}</a></li>`;
  });
  listHtml += '</ul>';
  reply.type('text/html').send(layout('Home', listHtml));
});

// Custom route for the "Create" form (not in OpenAPI but needed for the webapp to function)
fastify.get('/entries/new', async (request, reply) => {
  const form = `
    <h1>Create New Entry</h1>
    <form method="POST" action="/entries">
      <p>Title: <br><input name="title" required style="width:100%"></p>
      <p>Content: <br><textarea name="content" required style="width:100%; height:200px"></textarea></p>
      <p>Your Name: <br><input name="createdBy" required></p>
      <button type="submit">Save Entry</button>
    </form>
  `;
  reply.type('text/html').send(layout('New Entry', form));
});

fastify.post('/entries', async (request, reply) => {
  let body;
  if (request.headers['content-type'] === 'application/json') {
    body = request.body;
  } else {
    // Handle form-urlencoded for the web UI
    const queryString = await request.request.text();
    body = Object.fromEntries(new URLSearchParams(queryString));
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

  const html = `
    <h1>${entry.title}</h1>
    <div class="entry-box">
      <p>${entry.content.replace(/\n/g, '<br>')}</p>
    </div>
    <hr>
    <p><small>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</small></p>
    <p><small>Contributors: ${contributorList}</small></p>
    <p><a href="/entries/${entryId}/edit">Edit this page</a> | <a href="/entries/${entryId}/edits">View History</a></p>
  `;
  reply.type('text/html').send(layout(entry.title, html));
});

// Custom route for Edit form
fastify.get('/entries/:entryId/edit', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

  const form = `
    <h1>Edit: ${entry.title}</h1>
    <form method="PUT" action="/entries/${entryId}">
      <p>Content: <br><textarea name="content" required style="width:100%; height:200px">${entry.content}</textarea></p>
      <p>Your Name: <br><input name="modifiedBy" required></p>
      <p>Edit Summary: <br><input name="summary" required style="width:100%"></p>
      <button type="submit">Save Changes</button>
    </form>
    <script>
      // Fastify/HTTP doesn't support PUT via standard HTML forms
      // We intercept the submit and use fetch
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
  reply.type('text/html').send(layout(entry.title, form));
});

fastify.put('/entries/:entryId', async (request, reply) => {
  const { entryId } = request.params;
  const { content, modifiedBy, summary } = request.body;
  const now = new Date().toISOString();

  const entry = await dbGet('SELECT id FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send({ error: 'Entry not found' });

  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
    [content, modifiedBy, now, entryId]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [entryId, content, modifiedBy, summary, now]);

  const updated = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  reply.send(updated);
});

fastify.get('/entries/:entryId/edits', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT id FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

  const edits = await dbAll('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [entryId]);
  
  let historyHtml = `<h1>Edit History for Entry ${entryId}</h1>`;
  
  for (let i = 0; i < edits.length; i++) {
    const edit = edits[i];
    const prev = edits[i+1];
    let diff = '';
    
    if (prev) {
      // Simple line-based diff simulation
      const oldLines = prev.content.split('\n');
      const newLines = edit.content.split('\n');
      diff = `<pre>`;
      newLines.forEach((line, idx) => {
        if (oldLines[idx] !== line) {
          diff += `<span class="diff-old">${oldLines[idx] || ''}</span>\n`;
          diff += `<span class="diff-new">${line}</span>\n`;
        } else {
          diff += `${line}\n`;
        }
      });
      diff += `</pre>`;
    } else {
      diff = `<p>Initial version</p>`;
    }

    historyHtml += `
      <div class="entry-box" style="margin-bottom: 20px;">
        <strong>${edit.modifiedBy}</strong> (${edit.modifiedAt})<br>
        <em>Summary: ${edit.summary}</em>
        ${diff}
      </div>
    `;
  }

  reply.type('text/html').send(layout('History', historyHtml));
});

// Start server
fastify.listen({ port: 5000, host: '0.0.0.0' }, (err, address) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log(`Server listening at ${address}`);
});