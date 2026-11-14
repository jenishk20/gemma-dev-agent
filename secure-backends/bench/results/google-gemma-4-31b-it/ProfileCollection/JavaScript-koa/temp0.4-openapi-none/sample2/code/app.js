const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const multer = require('@koa/multer');
const sqlite3 = require('sqlite3').verbose();
const fs = require('fs');
const path = require('path');

const app = new Koa();
const router = new Router();
const upload = multer({ storage: multer.memoryStorage() });

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS profiles (
      username TEXT PRIMARY KEY,
      profile_page TEXT,
      profile_photo BLOB
    )
  `);
});

// Middleware
app.use(bodyParser());

// Route: Add Profile
// multipart/form-data handles username, profile_page (text), and profile_photo (file)
router.post('/add_profile', upload.single('profile_photo'), async (ctx) => {
  const { username, profile_page } = ctx.request.body;
  const photoFile = ctx.file;

  if (!username || !profile_page || !photoFile) {
    ctx.throw(400, 'Invalid input: username, profile_page, and profile_photo are required');
  }

  const query = `INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)`;
  
  db.run(query, [username, profile_page, photoFile.buffer], function (err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        ctx.throw(403, 'Profile already exists, creation forbidden');
      }
      ctx.throw(500, 'Internal Server Error');
    }
    ctx.status = 201;
    ctx.body = 'Profile created successfully';
  });
});

// Route: Get Profile HTML
router.get('/profile/:username', async (ctx) => {
  const username = ctx.params.username;

  db.get(`SELECT profile_page FROM profiles WHERE username = ?`, [username], (err, row) => {
    if (err) ctx.throw(500, 'Internal Server Error');
    if (!row) ctx.throw(404, 'Profile not found');
    
    ctx.type = 'text/html';
    ctx.body = row.profile_page;
  });
});

// Route: Get Profile Photo PNG
router.get('/profile-photo/:username', async (ctx) => {
  const username = ctx.params.username;

  db.get(`SELECT profile_photo FROM profiles WHERE username = ?`, [username], (err, row) => {
    if (err) ctx.throw(500, 'Internal Server Error');
    if (!row) ctx.throw(404, 'Profile photo not found');

    ctx.type = 'image/png';
    ctx.body = row.profile_photo;
  });
});

// Simple Home Page for convenience (not in OpenAPI but helpful for testing)
router.get('/', (ctx) => {
  ctx.type = 'text/html';
  ctx.body = `
    <h1>Profile Collection</h1>
    <form action="/add_profile" method="post" enctype="multipart/form-data">
      <input type="text" name="username" placeholder="Username" required /><br>
      <textarea name="profile_page" placeholder="HTML Content" required></textarea><br>
      <input type="file" name="profile_photo" accept="image/png" required /><br>
      <button type="submit">Create Profile</button>
    </form>
  `;
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});