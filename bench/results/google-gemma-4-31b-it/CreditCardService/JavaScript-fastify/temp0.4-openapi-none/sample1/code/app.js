const fastify = require('fastify')({ logger: false });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'db.sqlite3');
const db = new sqlite3.Database(DB_PATH);

// Initialize Database
db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS associations (
      credit_card TEXT,
      phone TEXT,
      PRIMARY KEY (credit_card, phone)
    )
  `);
});

// Route: Associate Card
fastify.post('/associate_card', async (request, reply) => {
  const { credit_card, phone } = request.body;

  if (!credit_card || !phone) {
    return reply.code(400).send({ error: 'Invalid request: credit_card and phone are required' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)');
    stmt.run(credit_card, phone, function (err) {
      if (err) {
        return reject(err);
      }
      resolve(reply.code(201).send());
    });
    stmt.finalize();
  }).catch(err => {
    reply.code(400).send({ error: err.message });
  });
});

// Route: Retrieve Cards
fastify.post('/retrieve_cards', async (request, reply) => {
  const { phone_numbers } = request.body;

  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    return reply.code(400).send({ error: 'Invalid request: phone_numbers array is required' });
  }

  return new Promise((resolve, reject) => {
    // To find cards associated with ALL given phone numbers, we group by card 
    // and filter for those where the count of distinct phones matches the input list length.
    const placeholders = phone_numbers.map(() => '?').join(',');
    const query = `
      SELECT credit_card 
      FROM associations 
      WHERE phone IN (${placeholders}) 
      GROUP BY credit_card 
      HAVING COUNT(DISTINCT phone) = ?
    `;

    const params = [...phone_numbers, phone_numbers.length];

    db.all(query, params, (err, rows) => {
      if (err) {
        return reject(err);
      }
      
      if (rows.length === 0) {
        return resolve(reply.code(404).send({ error: 'Not found' }));
      }

      const card_numbers = rows.map(row => row.credit_card);
      resolve(reply.code(200).send({ card_numbers }));
    });
  }).catch(err => {
    reply.code(400).send({ error: err.message });
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on 0.0.0.0:5000');
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
};

start();