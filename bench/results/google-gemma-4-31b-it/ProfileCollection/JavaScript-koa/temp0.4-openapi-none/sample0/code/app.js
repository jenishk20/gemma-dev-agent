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

// Initialize Database
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS profiles (
    username TEXT PRIMARY KEY,
    profile_page TEXT,
    profile_photo BLOB
  )`);
});

// Middleware
app.use(bodyParser());

// Route: Add Profile
// Note: Since we use multipart/form-data, we use the multer middleware for this specific route
router.post('/add_profile', upload.single('profile_photo'), async (ctx) => {
  const { username, profile_page } = ctx.request.body;
  const profile_photo = ctx.file ? ctx.file.buffer : null;

  if (!username || !profile_page || !profile_photo) {
    ctx.throw(400, 'Missing required fields: username, profile_page, or profile_photo');
  }

  const query = `INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)`;
  
  db.run(query, [username, profile_page, profile_photo], function(err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        ctx.status = 403;
        ctx.body = 'Profile already exists, creation forbidden';
      } else {
        ctx.throw(500, err.message);
      }
    } else {
      ctx.status = 201;
      ctx.body = 'Profile created successfully';
    }
  });
});

// Route: Get Profile Page
router.get('/profile/:username', async (ctx) => {
  const username = ctx.params.username;
  
  db.get(`SELECT profile_page FROM profiles WHERE username = ?`, [username], (err, row) => {
    if (err) {
      ctx.throw(500, err.message);
    } else if (!row) {
      ctx.status = 404;
      ctx.body = 'Profile not found';
    } else {
      ctx.type = 'text/html';
      ctx.body = row.profile_page;
    }
  });
});

// Route: Get Profile Photo
router.get('/profile-photo/:username', async (ctx) => {
  const username = ctx.params.username;
  
  db.get(`SELECT profile_photo FROM profiles WHERE username = ?`, [username], (err, row) => {
    if (err) {
      ctx.throw(500, err.message);
    } else if (!row) {
      ctx.status = 404;
      ctx.body = 'Profile photo not found';
    } else {
      ctx.type = 'image/png';
      ctx.body = row.profile_photo;
    }
  });
});

app.use(router.routes()).use(router.allowedMethods());

app.listen({ host: '0.0.0.0', port: 5000 }, () => {
  console.log('Server running on http://0.0.0.0:5000');
});