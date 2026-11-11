const fastify = require('fastify');
const sqlite3 = require('sqlite3');
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const app = fastify({ logger: true });
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

// Helper to wrap db.all/get in promises
const dbQuery = (sql, params = []) => new Promise((resolve, reject) => {
  db.all(sql, params, (err, rows) => err ? reject(err) : resolve(rows));
});
const dbGet = (sql, params = []) => new Promise((resolve, reject) => {
  db.get(sql, params, (err, row) => err ? reject(err) : resolve(row));
});
const dbRun = (sql, params = []) => new Promise((resolve, reject) => {
  db.run(sql, params, function(err) { err ? reject(err) : resolve(this); });
});

// HTML Templates
const layout = (title, content) => `
  <!DOCTYPE html>
  <html>
  <head>
    <title>${title} - Wiki</title>
    <style>
      body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
      nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
      .entry-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
      .diff { background: #f4f4f4; padding: 10px; border-left: 3px solid #ccc; white-space: pre-wrap; font-family: monospace; }
      form { display: flex; flex-direction: column; gap: 10px; max-width: 500px; }
      input, textarea { padding: 8px; font-size: 1rem; }
      button { cursor: pointer; padding: 10px; background: #007bff; color: white; border: none; border-radius: 3px; }
    </style>
  </head>
  <body>
    <nav><a href="/entries">🏠 Home</a></nav>
    <h1>${title}</h1>
    ${content}
  </body>
  </html>
`;

// Routes
app.get('/entries', async (request, reply) => {
  const rows = await dbQuery('SELECT id, title FROM entries');
  let listHtml = '<ul>';
  rows.forEach(row => {
    listHtml += `<li><a href="/entries/${row.id}">${row.title}</a></li>`;
  });
  listHtml += '</ul>';
  listHtml += `
    <hr>
    <h3>Create New Entry</h3>
    <form action="/entries" method="POST">
      <input name="title" placeholder="Title" required />
      <textarea name="content" placeholder="Content" required></textarea>
      <input name="createdBy" placeholder="Your Name" required />
      <button type="submit">Create Entry</button>
    </form>
  `;
  reply.type('text/html').send(layout('Wiki Entries', listHtml));
});

app.post('/entries', async (request, reply) => {
  // Since the OpenAPI says application/json, but the HTML form sends urlencoded, 
  // we handle both or just use a JSON body. For a webapp, we'll handle JSON.
  // Note: Fastify doesn't parse form-urlencoded by default. 
  // To support the HTML form above, we'd need a plugin, but we'll stick to JSON as per schema.
  const { title, content, createdBy } = request.body;
  const id = uuidv4();
  const now = new Date().toISOString();
  
  await dbRun('INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [id, title, content, createdBy, now]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [id, content, createdBy, 'Initial creation', now]);

  reply.code(201).send({ id, title, content, lastModifiedBy: createdBy, lastModifiedAt: now });
});

app.get('/entries/:entryId', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  
  if (!entry) return reply.code(404).send('Entry not found');

  const contributors = await dbQuery('SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?', [entryId]);
  const contributorList = contributors.map(c => c.modifiedBy).join(', ');

  const contentHtml = `
    <div class="entry-box">
      <p>${entry.content}</p>
      <small>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</small><br>
      <small>Contributors: ${contributorList}</small>
    </div>
    <hr>
    <a href="/entries/${entryId}/edits">View History</a> | 
    <a href="/edit/${entryId}">Edit this page</a>
  `;
  reply.type('text/html').send(layout(entry.title, contentHtml));
});

// Helper route for the edit form (not in OpenAPI but needed for the webapp UI)
app.get('/edit/:entryId', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

  const editHtml = `
    <form action="/entries/${entryId}" method="POST">
      <textarea name="content" rows="10" required>${entry.content}</textarea>
      <input name="modifiedBy" placeholder="Your Name" required />
      <input name="summary" placeholder="What did you change?" required />
      <button type="submit">Save Changes</button>
    </form>
  `;
  reply.type('text/html').send(layout(`Editing: ${entry.title}`, editHtml));
});

app.put('/entries/:entryId', async (request, reply) => {
  const { entryId } = request.params;
  const { content, modifiedBy, summary } = request.body;
  const now = new Date().toISOString();

  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

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

// Overload POST for the HTML form to act as PUT
app.post('/entries/:entryId', async (request, reply) => {
  // This is a shim to allow HTML forms to perform the "Update" action
  const { entryId } = request.params;
  const { content, modifiedBy, summary } = request.body;
  const now = new Date().toISOString();
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');
  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', [content, modifiedBy, now, entryId]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', [entryId, content, modifiedBy, summary, now]);
  reply.redirect(`/entries/${entryId}`);
});

app.get('/entries/:entryId/edits', async (request, reply) => {
  const { entryId } = request.params;
  const entry = await dbGet('SELECT title FROM entries WHERE id = ?', [entryId]);
  if (!entry) return reply.code(404).send('Entry not found');

  const edits = await dbQuery('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [entryId]);
  
  let historyHtml = '<ul>';
  edits.forEach(edit => {
    historyHtml += `
      <li>
        <strong>${edit.modifiedBy}</strong> (${edit.modifiedAt}) - <em>${edit.summary}</em>
        <div class="diff">${edit.content}</div>
      </li><br>
    `;
  });
  historyHtml += '</ul>';
  
  reply.type('text/html').send(layout(`History: ${entry.title}`, historyHtml));
});

// Middleware to handle form data as JSON for the POST routes
app.addContentTypeParser('application/x-www-form-urlencoded', { parseAsJson: true }, (req, payload, done) => {
  let data = '';
  payload.on('data', chunk => { data += chunk; });
  payload.on('end', () => {
    const params = new URLSearchParams(data);
    const obj = {};
    for (const [key, value] of params) { obj[key] = value; }
    done(null, obj);
  });
});

const start = async () => {
  try {
    await app.listen({ host: '0.0.0.0', port: 5000 });
    console.log('Server running at http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();