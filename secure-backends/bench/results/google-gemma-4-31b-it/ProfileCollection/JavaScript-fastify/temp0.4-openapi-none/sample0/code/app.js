const fastify = require('fastify')({ logger: true });
const multipart = require('@fastify/multipart');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

// Initialize Database
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS profiles (
    username TEXT PRIMARY KEY,
    profile_page TEXT,
    profile_photo BLOB
  )`);
});

// Register Multipart plugin for file uploads
fastify.register(multipart);

/**
 * POST /add_profile
 * Handles multipart/form-data: username, profile_page (text), profile_photo (file)
 */
fastify.post('/add_profile', async (request, reply) => {
  const data = await request.file();
  if (!data) {
    return reply.status(400).send({ error: 'No file uploaded' });
  }

  // We expect the file to be the profile_photo. 
  // We extract other fields from the form.
  const fields = data.fields;
  const username = fields.username?.value;
  const profile_page = fields.profile_page?.value;
  const photoBuffer = await data.toBuffer();

  if (!username || !profile_page) {
    return reply.status(400).send({ error: 'Missing username or profile_page' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)');
    stmt.run(username, profile_page, photoBuffer, function (err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          resolve(reply.status(403).send({ error: 'Profile already exists' }));
        } else {
          resolve(reply.status(500).send({ error: 'Database error' }));
        }
      } else {
        resolve(reply.status(201).send({ message: 'Profile created successfully' }));
      }
    });
    stmt.finalize();
  });
});

/**
 * GET /profile/{username}
 * Returns the HTML content of the profile
 */
fastify.get('/profile/{username}', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get('SELECT profile_page FROM profiles WHERE username = ?', [username], (err, row) => {
      if (err || !row) {
        resolve(reply.status(404).send({ error: 'Profile not found' }));
      } else {
        reply.type('text/html').send(row.profile_page);
        resolve();
      }
    });
  });
});

/**
 * GET /profile-photo/{username}
 * Returns the PNG binary data of the profile photo
 */
fastify.get('/profile-photo/{username}', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get('SELECT profile_photo FROM profiles WHERE username = ?', [username], (err, row) => {
      if (err || !row) {
        resolve(reply.status(404).send({ error: 'Photo not found' }));
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
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();