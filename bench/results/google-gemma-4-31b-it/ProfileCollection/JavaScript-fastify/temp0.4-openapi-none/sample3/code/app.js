const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

const app = fastify({ logger: true });

// Register multipart support for file uploads
app.register(multipart);

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

// Route: POST /add_profile
app.post('/add_profile', async (request, reply) => {
  const data = await request.file();
  if (!data) {
    return reply.code(400).send('Invalid input: No file uploaded');
  }

  // The multipart handler processes fields in order. 
  // We need to collect username, profile_page, and the file.
  let username = '';
  let profilePage = '';
  let profilePhoto = null;

  // Since @fastify/multipart handles streams, we iterate through the parts
  // Note: In a real production app, you'd handle the stream more robustly.
  // For this simple app, we'll use the helper to get fields.
  
  // We need to handle the multipart stream manually to get all fields
  const parts = request.parts();
  let part;
  
  const collected = {};

  for await (const part of request.parts()) {
    if (part.file) {
      // We assume the first file encountered is the profile_photo
      const buffer = await part.toBuffer();
      collected.profile_photo = buffer;
    } else {
      collected[part.fieldname] = part.value;
    }
  }

  username = collected.username;
  profilePage = collected.profile_page;
  profilePhoto = collected.profile_photo;

  if (!username || !profilePage || !profilePhoto) {
    return reply.code(400).send('Missing required fields: username, profile_page, or profile_photo');
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)');
    stmt.run(username, profilePage, profilePhoto, function(err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          resolve(reply.code(403).send('Profile already exists, creation forbidden'));
        } else {
          resolve(reply.code(500).send('Internal Server Error'));
        }
      } else {
        resolve(reply.code(201).send('Profile created successfully'));
      }
    });
    stmt.finalize();
  });
});

// Route: GET /profile/{username}
app.get('/profile/:username', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get('SELECT profile_page FROM profiles WHERE username = ?', [username], (err, row) => {
      if (err || !row) {
        resolve(reply.code(404).send('Profile not found'));
      } else {
        reply.type('text/html').send(row.profile_page);
        resolve();
      }
    });
  });
});

// Route: GET /profile-photo/{username}
app.get('/profile-photo/:username', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get('SELECT profile_photo FROM profiles WHERE username = ?', [username], (err, row) => {
      if (err || !row) {
        resolve(reply.code(404).send('Profile photo not found'));
      } else {
        reply.type('image/png').send(row.profile_photo);
        resolve();
      }
    });
  });
});

// Start server
const start = async () => {
  try {
    await app.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();