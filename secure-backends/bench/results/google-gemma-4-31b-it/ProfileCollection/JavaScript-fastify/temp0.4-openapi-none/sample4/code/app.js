const fastify = require('fastify')({ logger: true });
const multipart = require('@fastify/multipart');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');

// Initialize Fastify plugins
fastify.register(multipart);

// Database setup
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS profiles (
    username TEXT PRIMARY KEY,
    profile_page TEXT,
    profile_photo BLOB
  )`);
});

// Route: Add a new user profile
fastify.post('/add_profile', async (request, reply) => {
  const data = await request.file();
  if (!data) {
    return reply.code(400).send({ error: 'Invalid input: No file uploaded' });
  }

  // We expect multipart/form-data. 
  // @fastify/multipart provides a stream. We need to collect the fields.
  const fields = {};
  const parts = [];
  
  // Since multipart is a stream, we iterate through the parts
  // Note: In a real scenario, we'd handle the stream more robustly.
  // For this simple app, we'll process the fields and the file.
  
  // To handle multiple fields and a file in one request with @fastify/multipart:
  // We use the 'parts' iterator.
  const it = request.parts();
  let username = null;
  let profile_page = null;
  let profile_photo_buffer = null;

  for await (const part of it) {
    if (part.file) {
      // If it's a file field, we check the field name
      if (part.fieldname === 'profile_photo') {
        const buffer = await part.toBuffer();
        profile_photo_buffer = buffer;
      } else if (part.fieldname === 'profile_page') {
        // Sometimes HTML is sent as a file
        const buffer = await part.toBuffer();
        profile_page = buffer.toString();
      }
    } else {
      // It's a regular field
      if (part.fieldname === 'username') username = part.value;
      if (part.fieldname === 'profile_page') profile_page = part.value;
    }
  }

  if (!username || !profile_page || !profile_photo_buffer) {
    return reply.code(400).send({ error: 'Missing required fields: username, profile_page, or profile_photo' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)');
    stmt.run(username, profile_page, profile_photo_buffer, function(err) {
      if (err) {
        if (err.message.includes('UNIQUE constraint failed')) {
          resolve(reply.code(403).send({ error: 'Profile already exists' }));
        } else {
          resolve(reply.code(500).send({ error: err.message }));
        }
      } else {
        resolve(reply.code(201).send({ message: 'Profile created successfully' }));
      }
    });
    stmt.finalize();
  });
});

// Route: Get user profile HTML
fastify.get('/profile/{username}', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get('SELECT profile_page FROM profiles WHERE username = ?', [username], (err, row) => {
      if (err || !row) {
        resolve(reply.code(404).send({ error: 'Profile not found' }));
      } else {
        reply.header('Content-Type', 'text/html');
        resolve(reply.code(200).send(row.profile_page));
      }
    });
  });
});

// Route: Get user profile photo
fastify.get('/profile-photo/{username}', async (request, reply) => {
  const { username } = request.params;

  return new Promise((resolve) => {
    db.get('SELECT profile_photo FROM profiles WHERE username = ?', [username], (err, row) => {
      if (err || !row) {
        resolve(reply.code(404).send({ error: 'Profile photo not found' }));
      } else {
        reply.header('Content-Type', 'image/png');
        resolve(reply.code(200).send(row.profile_photo));
      }
    });
  });
});

// Start the server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();