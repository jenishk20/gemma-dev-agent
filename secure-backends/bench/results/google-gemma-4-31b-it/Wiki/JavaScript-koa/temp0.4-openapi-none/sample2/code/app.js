const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const app = new Koa();
const router = new Router();

// Database Setup
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
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

// Helper to wrap db.all/get/run in promises
const dbQuery = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.all(sql, params, (err, rows) => {
      if (err) reject(err);
      else resolve(rows);
    });
  });
};

const dbGet = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.get(sql, params, (err, row) => {
      if (err) reject(err);
      else resolve(row);
    });
  });
};

const dbRun = (sql, params = []) => {
  return new Promise((resolve, reject) => {
    db.run(sql, params, function(err) {
      if (err) reject(err);
      else resolve({ id: this.lastID });
    });
  });
};

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
      .diff { background: #f4f4f4; padding: 10px; border-left: 3px solid #ccc; white-space: pre-wrap; margin: 10px 0; }
      form { display: flex; flex-direction: column; gap: 10px; max-width: 400px; }
      textarea { height: 200px; }
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

// GET /entries - List all entries
router.get('/entries', async (ctx) => {
  const rows = await dbQuery('SELECT id, title FROM entries');
  const list = rows.map(row => `<li><a href="/entries/${row.id}">${row.title}</a></li>`).join('');
  
  const content = `
    <p>Welcome to the Wiki! Create a new entry below.</p>
    <ul>${list || 'No entries yet.'}</ul>
    <hr>
    <h3>Create New Entry</h3>
    <form action="/entries" method="POST">
      <input name="title" placeholder="Title" required />
      <textarea name="content" placeholder="Content" required></textarea>
      <input name="createdBy" placeholder="Your Name" required />
      <button type="submit">Create</button>
    </form>
  `;
  ctx.type = 'text/html';
  ctx.body = layout('Wiki Entries', content);
});

// POST /entries - Create new entry
router.post('/entries', async (ctx) => {
  // Handle both JSON and Form Data (since we provide an HTML form)
  const body = ctx.request.body;
  const { title, content, createdBy } = body;

  if (!title || !content || !createdBy) {
    ctx.throw(400, 'Missing required fields');
  }

  const id = uuidv4();
  const now = new Date().toISOString();

  await dbRun('INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [id, title, content, createdBy, now]);
  
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [id, content, createdBy, 'Initial creation', now]);

  ctx.status = 201;
  ctx.body = { id, title, content, lastModifiedBy: createdBy, lastModifiedAt: now };
});

// GET /entries/{entryId} - View entry
router.get('/entries/:entryId', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const content = `
    <div class="entry-box">
      <p>${entry.content}</p>
      <small>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</small>
    </div>
    <hr>
    <div style="display:flex; gap:10px;">
      <a href="/entries/${entry.id}/edits">📜 View History</a>
      <a href="/entries/${entry.id}/edit">✏️ Edit Page</a>
    </div>
  `;
  ctx.type = 'text/html';
  ctx.body = layout(entry.title, content);
});

// Special route for the edit form (not in OpenAPI but needed for the webapp UI)
router.get('/entries/:entryId/edit', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const content = `
    <form action="/entries/${entry.id}" method="POST">
      <textarea name="content" required>${entry.content}</textarea>
      <input name="modifiedBy" placeholder="Your Name" required />
      <input name="summary" placeholder="What did you change?" required />
      <button type="submit">Save Changes</button>
    </form>
  `;
  ctx.type = 'text/html';
  ctx.body = layout(`Editing: ${entry.title}`, content);
});

// PUT /entries/{entryId} - Update entry
// We use POST here to support the HTML form, but the logic implements the PUT requirement
router.post('/entries/:entryId', async (ctx) => {
  const entryId = ctx.params.entryId;
  const body = ctx.request.body;
  const { content, modifiedBy, summary } = body;

  if (!content || !modifiedBy || !summary) {
    ctx.throw(400, 'Missing required fields');
  }

  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const now = new Date().toISOString();

  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
    [content, modifiedBy, now, entryId]);
  
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [entryId, content, modifiedBy, summary, now]);

  ctx.body = { ...entry, content, lastModifiedBy: modifiedBy, lastModifiedAt: now };
});

// GET /entries/{entryId}/edits - History
router.get('/entries/:entryId/edits', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const edits = await dbQuery('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [ctx.params.entryId]);
  
  let historyHtml = '<ul>';
  edits.forEach((edit, index) => {
    historyHtml += `
      <li>
        <strong>${edit.modifiedBy}</strong> (${edit.modifiedAt}) - <em>${edit.summary}</em>
        <div class="diff">${edit.content}</div>
      </li>`;
  });
  historyHtml += '</ul>';

  ctx.type = 'text/html';
  ctx.body = layout(`History: ${entry.title}`, historyHtml);
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Wiki server running on http://0.0.0.0:5000');
});