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
const dbGet = (query, params = []) => new Promise((res, rej) => {
  db.get(query, params, (err, row) => err ? rej(err) : res(row));
});
const dbAll = (query, params = []) => new Promise((res, rej) => {
  db.all(query, params, (err, rows) => err ? rej(err) : res(rows));
});
const dbRun = (query, params = []) => new Promise((res, rej) => {
  db.run(query, params, function(err) { err ? rej(err) : res(this); });
});

// HTML Templates
const layout = (title, body) => `
  <!DOCTYPE html>
  <html>
  <head>
    <title>${title} - Wiki</title>
    <style>
      body { font-family: sans-serif; margin: 40px; line-height: 1.6; }
      nav { margin-bottom: 20px; }
      .entry-box { border: 1px solid #ccc; padding: 20px; border-radius: 5px; }
      .diff { background: #f4f4f4; padding: 10px; border-left: 4px solid #ccc; white-space: pre-wrap; }
      form { display: flex; flex-direction: column; gap: 10px; max-width: 500px; }
      input, textarea { padding: 8px; }
    </style>
  </head>
  <body>
    <nav><a href="/entries">🏠 Home</a></nav>
    <h1>${title}</h1>
    ${body}
  </body>
  </html>
`;

// Routes

// GET /entries - List all entries
router.get('/entries', async (ctx) => {
  const rows = await dbAll('SELECT id, title FROM entries');
  const list = rows.map(row => `<li><a href="/entries/${row.id}">${row.title}</a></li>`).join('');
  const body = `
    <p>Welcome to the Wiki!</p>
    <ul>${list || 'No entries yet.'}</ul>
    <hr/>
    <h3>Create New Entry</h3>
    <form action="/entries" method="POST">
      <input name="title" placeholder="Title" required />
      <textarea name="content" placeholder="Content" required></textarea>
      <input name="createdBy" placeholder="Your Name" required />
      <button type="submit">Create</button>
    </form>
  `;
  ctx.type = 'text/html';
  ctx.body = layout('Wiki Entries', body);
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

// GET /entries/{id} - View entry
router.get('/entries/:entryId', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) {
    ctx.throw(404);
  }

  const body = `
    <div class="entry-box">
      <p>${entry.content}</p>
      <small>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</small>
    </div>
    <hr/>
    <a href="/entries/${entry.id}/edits">View History</a> | 
    <a href="/edit/${entry.id}">Edit this page</a>
  `;
  ctx.type = 'text/html';
  ctx.body = layout(entry.title, body);
});

// Special route for the Edit Form (since OpenAPI PUT is JSON, we need a GET for the HTML form)
router.get('/edit/:entryId', async (ctx) => {
  const entry = await dbGet('SELECT * FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404);

  const body = `
    <form action="/entries/${entry.id}" method="POST" enctype="application/x-www-form-urlencoded">
      <input type="hidden" name="_method" value="PUT">
      <textarea name="content" rows="10">${entry.content}</textarea>
      <input name="modifiedBy" placeholder="Your Name" required />
      <input name="summary" placeholder="What did you change?" required />
      <button type="submit">Save Changes</button>
    </form>
  `;
  ctx.type = 'text/html';
  ctx.body = layout(`Editing: ${entry.title}`, body);
});

// PUT /entries/{id} - Update entry
// Note: Since HTML forms only support GET/POST, we handle the logic here. 
// To satisfy the OpenAPI spec, we accept JSON. For the webapp, we'll allow a custom handler.
router.put('/entries/:entryId', async (ctx) => {
  const { content, modifiedBy, summary } = ctx.request.body;
  const entryId = ctx.params.entryId;
  const now = new Date().toISOString();

  const entry = await dbGet('SELECT id FROM entries WHERE id = ?', [entryId]);
  if (!entry) ctx.throw(404);

  await dbRun('UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?', 
    [content, modifiedBy, now, entryId]);
  await dbRun('INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)', 
    [entryId, content, modifiedBy, summary, now]);

  const updated = await dbGet('SELECT * FROM entries WHERE id = ?', [entryId]);
  ctx.body = updated;
});

// Middleware to handle HTML form "PUT" via POST + _method hidden field
router.post('/entries/:entryId', async (ctx, next) => {
  if (ctx.request.body._method === 'PUT') {
    ctx.method = 'PUT';
    return await next();
  }
  await next();
});

// GET /entries/{id}/edits - History
router.get('/entries/:entryId/edits', async (ctx) => {
  const entry = await dbGet('SELECT title FROM entries WHERE id = ?', [ctx.params.entryId]);
  if (!entry) ctx.throw(404);

  const edits = await dbAll('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [ctx.params.entryId]);
  
  let historyHtml = '<ul>';
  edits.forEach((edit, index) => {
    historyHtml += `
      <li>
        <strong>${edit.modifiedAt}</strong> by ${edit.modifiedBy}: <em>${edit.summary}</em>
        <div class="diff">${edit.content}</div>
      </li><br/>`;
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