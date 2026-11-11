const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

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
      body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
      nav { margin-bottom: 20px; }
      .entry-box { border: 1px solid #ccc; padding: 20px; border-radius: 8px; }
      .meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }
      .diff { background: #f4f4f4; padding: 10px; border-left: 4px solid #ccc; white-space: pre-wrap; margin: 10px 0; }
      form { display: flex; flex-direction: column; gap: 10px; max-width: 500px; }
      textarea { height: 200px; }
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
  listHtml += '<form action="/entries" method="POST" style="margin-bottom: 30px;">';
  listHtml += '<h3>Create New Entry</h3>';
  listHtml += '<input name="title" placeholder="Title" required /><br>';
  listHtml += '<textarea name="content" placeholder="Content" required></textarea><br>';
  listHtml += '<input name="createdBy" placeholder="Your Name" required /><br>';
  listHtml += '<button type="submit">Create</button></form>';
  
  if (rows.length === 0) {
    listHtml += '<p>No entries yet.</p>';
  } else {
    listHtml += '<ul>';
    rows.forEach(row => {
      listHtml += `<li><a href="/entries/${row.id}">${row.title}</a></li>`;
    });
    listHtml += '</ul>';
  }
  
  ctx.type = 'text/html';
  ctx.body = layout('Home', listHtml);
});

// POST /entries - Create entry
router.post('/entries', async (ctx) => {
  const { title, content, createdBy } = ctx.request.body;
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
  if (!entry) {
    ctx.throw(404, 'Entry not found');
  }

  let html = `<div class="entry-box">`;
  html += `<h1>${entry.title}</h1>`;
  html += `<div class="meta">Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</div>`;
  html += `<div class="content">${entry.content}</div>`;
  html += `<hr>`;
  html += `<a href="/entries/${entry.id}/edits">📜 View History</a> | `;
  html += `<a href="#edit">✏️ Edit</a>`;
  html += `</div>`;

  html += `
    <div id="edit" style="margin-top: 30px;">
      <h3>Edit Entry</h3>
      <form action="/entries/${entry.id}" method="PUT">
        <textarea name="content" required>${entry.content}</textarea><br>
        <input name="modifiedBy" placeholder="Your Name" required /><br>
        <input name="summary" placeholder="What did you change?" required /><br>
        <button type="submit">Save Changes</button>
      </form>
    </div>
  `;

  ctx.type = 'text/html';
  ctx.body = layout(entry.title, html);
});

// PUT /entries/{entryId} - Update entry
// Note: Since standard HTML forms don't support PUT, we handle it via bodyParser 
// but for the sake of the OpenAPI spec, we implement the PUT route.
// To make the HTML form work, we'll allow POST to act as PUT or use a hidden field.
// Here we implement PUT as requested by the schema.
router.put('/entries/:entryId', async (ctx) => {
  const { content, modifiedBy, summary } = ctx.request.body;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  
  if (!entry) {
    ctx.throw(404, 'Entry not found');
  }

  const now = new Date().toISOString();
  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
    [content, modifiedBy, now, ctx.params.entryId]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [ctx.params.entryId, content, modifiedBy, summary, now]);

  ctx.body = { 
    id: entry.id, 
    title: entry.title, 
    content, 
    lastModifiedBy: modifiedBy, 
    lastModifiedAt: now 
  };
});

// Overload POST to handle the HTML form "PUT" request for the UI
router.post('/entries/:entryId', async (ctx) => {
  // This is a shim for the HTML form which only supports GET/POST
  // We manually call the logic of the PUT route
  const { content, modifiedBy, summary } = ctx.request.body;
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) return ctx.throw(404);
  
  const now = new Date().toISOString();
  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
    [content, modifiedBy, now, ctx.params.entryId]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [ctx.params.entryId, content, modifiedBy, summary, now]);
  
  ctx.redirect(`/entries/${ctx.params.entryId}`);
});

// GET /entries/{entryId}/edits - History
router.get('/entries/:entryId/edits', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) {
    ctx.throw(404, 'Entry not found');
  }

  const edits = await dbQuery('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [ctx.params.entryId]);
  
  let html = `<h1>Edit History: ${entry.title}</h1>`;
  html += `<p><a href="/entries/${entry.id}">⬅️ Back to entry</a></p>`;
  
  edits.forEach((edit, index) => {
    html += `<div class="entry-box" style="margin-bottom: 15px;">`;
    html += `<strong>${edit.modifiedBy}</strong> - ${edit.modifiedAt}<br>`;
    html += `<em>Summary: ${edit.summary}</em>`;
    html += `<div class="diff">${edit.content}</div>`;
    html += `</div>`;
  });

  ctx.type = 'text/html';
  ctx.body = layout(`History - ${entry.title}`, html);
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Wiki server running on http://0.0.0.0:5000');
});