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
    title TEXT,
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
      .diff { background: #f4f4f4; padding: 10px; white-space: pre-wrap; font-family: monospace; }
      form { display: flex; flex-direction: column; gap: 10px; max-width: 400px; }
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
  const listHtml = rows.length 
    ? `<ul>${rows.map(r => `<li><a href="/entries/${r.id}">${r.title}</a></li>`).join('')}</ul>` 
    : '<p>No entries yet.</p>';
  
  const createForm = `
    <h3>Create New Entry</h3>
    <form action="/entries" method="POST">
      <input name="title" placeholder="Title" required /><br/>
      <textarea name="content" placeholder="Content" required></textarea><br/>
      <input name="createdBy" placeholder="Your Name" required /><br/>
      <button type="submit">Create</button>
    </form>
  `;

  ctx.type = 'text/html';
  ctx.body = layout('Home', `<h1>Wiki Entries</h1>${listHtml}<hr/>${createForm}`);
});

// POST /entries - Create new entry
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

// GET /entries/{entryId} - View specific entry
router.get('/entries/:entryId', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const content = `
    <h1>${entry.title}</h1>
    <div class="entry-box">
      <p>${entry.content}</p>
    </div>
    <p><small>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</small></p>
    <hr/>
    <a href="/entries/${entry.id}/edits">📜 View History</a> | 
    <a href="/entries/${entry.id}/edit">✏️ Edit Page</a>
  `;
  
  ctx.type = 'text/html';
  ctx.body = layout(entry.title, content);
});

// Helper route for the Edit UI (not explicitly in OpenAPI but needed for the webapp to function)
router.get('/entries/:entryId/edit', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const editForm = `
    <h1>Editing: ${entry.title}</h1>
    <form action="/entries/${entry.id}" method="POST" enctype="application/json">
      <!-- Since standard HTML forms don't send JSON, we'll use a small script or just a standard form and handle it -->
      <textarea name="content" required>${entry.content}</textarea><br/>
      <input name="modifiedBy" placeholder="Your Name" required /><br/>
      <input name="summary" placeholder="What did you change?" required /><br/>
      <button type="submit" onclick="submitJson(event)">Save Changes</button>
    </form>
    <script>
      async function submitJson(e) {
        e.preventDefault();
        const form = e.target;
        const data = {
          content: form.content.value,
          modifiedBy: form.modifiedBy.value,
          summary: form.summary.value
        };
        const res = await fetch('/entries/${entry.id}', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        if (res.ok) window.location.href = '/entries/${entry.id}';
        else alert('Error updating entry');
      }
    </script>
  `;
  ctx.type = 'text/html';
  ctx.body = layout('Edit Entry', editForm);
});

// PUT /entries/{entryId} - Update entry
router.put('/entries/:entryId', async (ctx) => {
  const { entryId } = ctx.params;
  const { content, modifiedBy, summary } = ctx.request.body;
  
  const entry = await dbGet('SELECT id FROM entries WHERE id = ?', [entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const now = new Date().toISOString();
  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
    [content, modifiedBy, now, entryId]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [entryId, content, modifiedBy, summary, now]);

  const updated = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  ctx.body = updated;
});

// GET /entries/{entryId}/edits - History
router.get('/entries/:entryId/edits', async (ctx) => {
  const { entryId } = ctx.params;
  const entry = await dbGet('SELECT title FROM entries WHERE id = ?', [entryId]);
  if (!entry) ctx.throw(404, 'Entry not found');

  const edits = await dbQuery('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [entryId]);
  
  let historyHtml = `<h1>History: ${entry.title}</h1>`;
  edits.forEach((edit, index) => {
    historyHtml += `
      <div class="entry-box" style="margin-bottom: 20px;">
        <strong>${edit.modifiedBy}</strong> - ${edit.modifiedAt}<br/>
        <em>Summary: ${edit.summary}</em>
        <div class="diff">${edit.content}</div>
      </div>
    `;
  });

  ctx.type = 'text/html';
  ctx.body = layout(`History - ${entry.title}`, historyHtml);
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Wiki server running on http://0.0.0.0:5000');
});