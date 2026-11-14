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

// Route: Add a new user profile
app.post('/add_profile', async (request, reply) => {
  const data = await request.file();
  
  if (!data) {
    return reply.code(400).send({ error: 'Invalid input: No file uploaded' });
  }

  // We expect the multipart form to contain username, profile_page, and profile_photo
  // Since @fastify/multipart handles files, we need to collect the fields
  const fields = {};
  const fileBuffers = {};

  // Process the multipart stream
  // Note: fastify-multipart provides a way to get all fields and files
  // In this simple implementation, we iterate through the parts
  
  // Re-fetching the parts manually because request.file() only gets the first file
  // We use the request.parts() async iterator for full multipart handling
  
  // Reset the request stream for the iterator
  // Since we already called request.file(), we need to handle the stream carefully.
  // Better approach: use request.saveFile or a custom parser.
});

// Redefining the POST handler to correctly handle multiple parts
app.post('/add_profile', async (request, reply) => {
  const parts = request.parts();
  const profile = {};
  let photoBuffer = null;

  for await (const part of parts) {
    if (part.file) {
      if (part.fieldname === 'profile_photo') {
        const buffer = await part.toBuffer();
        photoBuffer = buffer;
      } else {
        // If profile_page is sent as a file, read it as text
        const buffer = await part.toBuffer();
        profile[part.fieldname] = buffer.toString();
      }
    } else {
      // This is a regular field
      profile[part.fieldname] = part.value;
    }
  }

  const { username, profile_page } = profile;

  if (!username || !profile_page || !photoBuffer) {
    return reply.code(400).send({ error: 'Missing required fields: username, profile_page, or profile_photo' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)');
    stmt.run(username, profile_page, photoBuffer, function (err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          resolve(reply.code(403).send({ error: 'Profile already exists' }));
        } else {
          resolve(reply.code(500).send({ error: 'Database error' }));
        }
      } else {
        resolve(reply.code(201).send({ message: 'Profile created successfully' }));
      }
    });
    stmt.finalize();
  });
});

// Route: Get user profile HTML
app.get('/profile/:username', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get('SELECT profile_page FROM profiles WHERE username = ?', [username], (err, row) => {
      if (err || !row) {
        resolve(reply.code(404).send({ error: 'Profile not found' }));
      } else {
        reply.type('text/html').send(row.profile_page);
        resolve();
      }
    });
  });
});

// Route: Get user profile photo
app.get('/profile-photo/:username', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get('SELECT profile_photo FROM profiles WHERE username = ?', [username], (err, row) => {
      if (err || !row) {
        resolve(reply.code(404).send({ error: 'Profile photo not found' }));
      } else {
        reply.type('image/png').send(row.profile_photo);
        resolve();
      }
    });
  });
});

// Start the server
app.listen({ port: 5000, host: '0.0.0.0' }, (err, address) => {
  if (err) {
    console.error(err);
    process.exit(1);
  }
  console.log(`Server listening at ${address}`);
});