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
  db.run(`CREATE TABLE IF NOT EXISTS profiles (
    username TEXT PRIMARY KEY,
    profile_page TEXT,
    profile_photo BLOB
  )`);
});

app.use(bodyParser());

// Route: POST /add_profile
router.post('/add_profile', upload.single('profile_photo'), async (ctx) => {
  const { username, profile_page } = ctx.request.body;
  const profile_photo = ctx.file ? ctx.file.buffer : null;

  if (!username || !profile_page || !profile_photo) {
    ctx.throw(400, 'Invalid input: username, profile_page, and profile_photo are required');
  }

  const query = `INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)`;
  
  db.run(query, [username, profile_page, profile_photo], function(err) {
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

// Route: GET /profile/{username}
router.get('/profile/:username', async (ctx) => {
  const username = ctx.params.username;
  const query = `SELECT profile_page FROM profiles WHERE username = ?`;

  db.get(query, [username], (err, row) => {
    if (err) ctx.throw(500, 'Internal Server Error');
    if (!row) {
      ctx.throw(404, 'Profile not found');
    }
    ctx.type = 'text/html';
    ctx.body = row.profile_page;
  });
});

// Route: GET /profile-photo/{username}
router.get('/profile-photo/:username', async (ctx) => {
  const username = ctx.params.username;
  const query = `SELECT profile_photo FROM profiles WHERE username = ?`;

  db.get(query, [username], (err, row) => {
    if (err) ctx.throw(500, 'Internal Server Error');
    if (!row || !row.profile_photo) {
      ctx.throw(404, 'Profile photo not found');
    }
    ctx.type = 'image/png';
    ctx.body = row.profile_photo;
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});