const fastify = require('fastify')({ logger: false });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = path.join(__dirname, 'db.sqlite3');
const db = new sqlite3.Database(DB_PATH);

// Initialize Database
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS associations (
    card_number TEXT,
    phone_number TEXT,
    PRIMARY KEY (card_number, phone_number)
  )`);
});

// Route: Associate Card
fastify.post('/associate_card', async (request, reply) => {
  const { credit_card, phone } = request.body;

  if (!credit_card || !phone) {
    return reply.status(400).send({ error: 'Invalid request: credit_card and phone are required' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT OR IGNORE INTO associations (card_number, phone_number) VALUES (?, ?)');
    stmt.run(credit_card, phone, function (err) {
      if (err) {
        reject(err);
      } else {
        resolve(reply.status(201).send());
      }
    });
    stmt.finalize();
  }).catch(err => {
    reply.status(500).send({ error: 'Internal Server Error' });
  });
});

// Route: Retrieve Cards
fastify.post('/retrieve_cards', async (request, reply) => {
  const { phone_numbers } = request.body;

  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    return reply.status(400).send({ error: 'Invalid request: phone_numbers array is required' });
  }

  return new Promise((resolve, reject) => {
    // To find cards associated with ALL given phone numbers:
    // We group by card_number and count how many of the requested phones are associated with it.
    // If the count equals the length of the input array, the card is associated with all of them.
    const placeholders = phone_numbers.map(() => '?').join(',');
    const query = `
      SELECT card_number 
      FROM associations 
      WHERE phone_number IN (${placeholders}) 
      GROUP BY card_number 
      HAVING COUNT(DISTINCT phone_number) = ?
    `;

    db.all(query, [...phone_numbers, phone_numbers.length], (err, rows) => {
      if (err) {
        reject(err);
      } else {
        const card_numbers = rows.map(row => row.card_number);
        if (card_numbers.length === 0) {
          resolve(reply.status(404).send({ error: 'Not found' }));
        } else {
          resolve(reply.status(200).send({ card_numbers }));
        }
      }
    });
  }).catch(err => {
    reply.status(500).send({ error: 'Internal Server Error' });
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server listening on 0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();