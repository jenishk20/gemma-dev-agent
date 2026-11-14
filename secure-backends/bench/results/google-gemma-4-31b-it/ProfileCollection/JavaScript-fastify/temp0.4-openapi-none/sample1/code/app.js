const fastify = require('fastify');
const multipart = require('@fastify/multipart');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

const app = fastify();

// Register multipart for handling file uploads
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
    return reply.code(400).send('Invalid input: No file provided');
  }

  // We expect multipart/form-data. 
  // Since @fastify/multipart processes fields as they arrive, 
  // we need to collect all fields.
  const body = {};
  let profilePhotoBuffer = null;

  // Process the stream
  const parts = request.parts();
  for await (const part of parts) {
    if (part.type === 'field') {
      body[part.fieldname] = part.value;
    } else if (      part.type === 'file' && part.fieldname === 'profile_photo') {
      profilePhotoBuffer = await part.toBuffer();
    }
  }

  const { username, profile_page } = body;

  if (!username || !profile_page || !profilePhotoBuffer) {
    return reply.code(400).send('Invalid input: Missing username, profile_page, or profile_photo');
  }

  const query = `INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)`;
  
  try {
    await new Promise((resolve, reject) => {
      db.run(query, [username, profile_page, profilePhotoBuffer], function(err) {
        if (err) return reject(err);
        resolve();
      });
    });
    return reply.code(201).send('Profile created successfully');
  } catch (err) {
    if (err.message.includes('UNIQUE constraint failed')) {
      return reply.code(403).send('Profile already exists, creation forbidden');
    }
    return reply.code(500).send('Internal Server Error');
  }
});

// Route: GET /profile/{username}
app.get('/profile/:username', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get(`SELECT profile_page FROM profiles WHERE username = ?`, [username], (err, row) => {
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
    db.get(`SELECT profile_photo FROM profiles WHERE username = ?`, [username], (err, row) => {
      if (err || !row) {
        resolve(reply.code(404).send('Profile photo not found'));
      } else {
        reply.type('image/png').send(row.profile_photo);
        resolve();
      }
    });
  });
});

// Start the server
const start = async () => {
  try {
    await app.listen({ host: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();