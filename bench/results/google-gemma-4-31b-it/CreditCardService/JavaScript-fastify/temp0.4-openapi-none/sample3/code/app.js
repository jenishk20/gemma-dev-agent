const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

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
    return reply.status(400).send({ error: 'Invalid request: credit_card and phone are required' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT OR IGNORE INTO associations (credit_card, phone) VALUES (?, ?)');
    stmt.run(credit_card, phone, function (err) {
      if (err) {
        console.error(err);
        resolve(reply.status(500).send({ error: 'Internal Server Error' }));
      } else {
        resolve(reply.status(201).send({ message: 'Association created successfully' }));
      }
    });
    stmt.finalize();
  });
});

// Route: Retrieve Cards
fastify.post('/retrieve_cards', async (request, reply) => {
  const { phone_numbers } = request.body;

  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    return reply.status(400).send({ error: 'Invalid request: phone_numbers array is required' });
  }

  return new Promise((resolve) => {
    // We need cards that are associated with ALL provided phone numbers.
    // We group by credit_card and count how many of the provided phone numbers match.
    // If the count equals the length of the input array, the card is associated with all of them.
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
        console.error(err);
        resolve(reply.status(500).send({ error: 'Internal Server Error' }));
      } else {
        const card_numbers = rows.map(row => row.credit_card);
        if (card_numbers.length === 0) {
          resolve(reply.status(404).send({ error: 'Not found' }));
        } else {
          resolve(reply.status(200).send({ card_numbers }));
        }
      }
    });
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();