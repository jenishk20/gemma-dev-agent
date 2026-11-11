const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const PORT = 5000;
const HOST = '0.0.0.0';
const DB_PATH = path.join(__dirname, 'db.sqlite3');

const app = fastify({ logger: true });
const db = new sqlite3.Database(DB_PATH);

// Initialize Database
db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS card_phone_associations (
      credit_card TEXT,
      phone TEXT,
      PRIMARY KEY (credit_card, phone)
    )
  `);
});

// POST /associate_card
app.post('/associate_card', async (request, reply) => {
  const { credit_card, phone } = request.body;

  if (!credit_card || !phone) {
    return reply.status(400).send({ error: 'Invalid request: credit_card and phone are required' });
  }

  return new Promise((resolve, reject) => {
    const stmt = db.prepare('INSERT OR IGNORE INTO card_phone_associations (credit_card, phone) VALUES (?, ?)');
    stmt.run(credit_card, phone, function (err) {
      if (err) {
        app.log.error(err);
        return resolve(reply.status(500).send({ error: 'Internal Server Error' }));
      }
      stmt.finalize();
      resolve(reply.status(201).send());
    });
  });
});

// POST /retrieve_cards
app.post('/retrieve_cards', async (request, reply) => {
  const { phone_numbers } = request.body;

  if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
    return reply.status(400).send({ error: 'Invalid request: phone_numbers array is required' });
  }

  return new Promise((resolve) => {
    // We need cards that are associated with ALL provided phone numbers.
    // We group by credit_card and filter for those where the count of distinct phones 
    // matching the input list equals the length of the input list.
    const placeholders = phone_numbers.map(() => '?').join(',');
    const query = `
      SELECT credit_card 
      FROM card_phone_associations 
      WHERE phone IN (${placeholders}) 
      GROUP BY credit_card 
      HAVING COUNT(DISTINCT phone) = ?
    `;

    const params = [...phone_numbers, phone_numbers.length];

    db.all(query, params, (err, rows) => {
      if (err) {
        app.log.error(err);
        return resolve(reply.status(500).send({ error: 'Internal Server Error' }));
      }

      if (rows.length === 0) {
        return resolve(reply.status(404).send({ error: 'Not found' }));
      }

      const card_numbers = rows.map(row => row.credit_card);
      resolve(reply.status(200).send({ card_numbers }));
    });
  });
});

// Start Server
const start = async () => {
  try {
    await app.listen({ port: PORT, host: HOST });
    console.log(`Server listening on ${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();