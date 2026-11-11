const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');

const app = new Koa();
const router = new Router();
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
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

// Helper to wrap db.get/all in promises
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
      else resolve(this);
    });
  });
};

// HTML Templates
const layout = (title, content) => `
  <!DOCTYPE html>
  <html>
  <head>
    <title>${title} - Wiki</title>
    <style>
      body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
      nav { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
      .entry-box { border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
      .diff { background: #f4f4f4; padding: 10px; border-left: 4px solid #ccc; white-space: pre-wrap; font-family: monospace; }
      form { display: flex; flex-direction: column; gap: 10px; max-width: 400px; }
      textarea { height: 150px; }
    </style>
  </head>
  <body>
    <nav><a href="/entries">🏠 Home</a></nav>
    ${content}
  </body>
  </html>
`;

// Routes

// GET /entries - List all entries
router.get('/entries', async (ctx) => {
  const rows = await dbQuery('SELECT id, title FROM entries');
  let listHtml = '<h1>Wiki Entries</h1>';
  listHtml += '<p><a href="/entries/new">➕ Create New Entry</a></p><ul>';
  rows.forEach(row => {
    listHtml += `<li><a href="/entries/${row.id}">${row.title}</a></li>`;
  });
  listHtml += '</ul>';
  
  ctx.type = 'text/html';
  ctx.body = layout('Home', listHtml);
});

// POST /entries - Create entry
router.post('/entries', async (ctx) => {
  const { title, content, createdBy } = ctx.request.body;
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

// GET /entries/{id} - View entry
router.get('/entries/:entryId', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  let html = `<h1>${entry.title}</h1>`;
  html += `<div class="entry-box">${entry.content}</div>`;
  html += `<p><small>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</small></p>`;
  html += `<p><a href="/entries/${entry.id}/edit">📝 Edit this page</a> | <a href="/entries/${entry.id}/edits">📜 History</a></p>`;

  ctx.type = 'text/html';
  ctx.body = layout(entry.title, html);
});

// PUT /entries/{id} - Update entry
router.put('/entries/:entryId', async (ctx) => {
  const entry = await dbGet('SELECT id FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const { content, modifiedBy, summary } = ctx.request.body;
  if (!content || !modifiedBy || !summary) {
    ctx.throw(400, 'Missing required fields');
  }

  const now = new Date().toISOString();
  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
    [content, modifiedBy, now, ctx.params.entryId]);
  
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [ctx.params.entryId, content, modifiedBy, summary, now]);

  const updated = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  ctx.body = updated;
});

// GET /entries/{id}/edits - History
router.get('/entries/:entryId/edits', async (ctx) => {
  const entry = await dbGet('SELECT id, title FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const edits = await dbQuery('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [ctx.params.entryId]);
  
  let html = `<h1>History: ${entry.title}</h1>`;
  html += '<a href="/entries/' + entry.id + '">⬅️ Back to entry</a><br><br>';
  
  edits.forEach((edit, index) => {
    html += `<div class="entry-box">`;
    html += `<strong>${edit.modifiedBy}</strong> - ${edit.modifiedAt}<br>`;
    html += `<em>Summary: ${edit.summary}</em>`;
    html += `<div class="diff">${edit.content}</div>`;
    html += `</div>`;
  });

  ctx.type = 'text/html';
  ctx.body = layout(`History - ${entry.title}`, html);
});

// Helper routes for the UI (not strictly in OpenAPI but needed for the webapp to be usable)
router.get('/entries/new', async (ctx) => {
  let html = `<h1>Create New Entry</h1>
    <form action="/entries" method="POST" enctype="application/json">
      <label>Title</label><input name="title" required>
      <label>Content</label><textarea name="content" required></textarea>
      <label>Your Name</label><input name="createdBy" required>
      <button type="submit">Save Entry</button>
    </form>
    <script>
      document.querySelector('form').onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        const res = await fetch('/entries', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        if (res.ok) window.location.href = '/entries';
      };
    </script>
  `;
  ctx.type = 'text/html';
  ctx.body = layout('New Entry', html);
});

router.get('/entries/:entryId/edit', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  let html = `<h1>Editing: ${entry.title}</h1>
    <form id="editForm">
      <label>Content</label><textarea name="content" required>${entry.content}</textarea>
      <label>Your Name</label><input name="modifiedBy" required>
      <label>Edit Summary</label><input name="summary" required>
      <button type="submit">Save Changes</button>
    </form>
    <script>
      document.getElementById('editForm').onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());
        const res = await fetch('/entries/${ctx.params.entryId}', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        if (res.ok) window.location.href = '/entries/${ctx.params.entryId}';
      };
    </script>
  `;
  ctx.type = 'text/html';
  ctx.body = layout(`Edit ${entry.title}`, html);
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Wiki server running on http://0.0.0.0:5000');
});