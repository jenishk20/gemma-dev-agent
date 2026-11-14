const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const PORT = 5000;
const HOST = '0.0.0.0';
const DB_PATH = path.join(__dirname, 'db.sqlite3');

async function start() {
  const app = fastify({ logger: true });
  
  // Initialize SQLite Database
  const db = new sqlite3.Database(DB_PATH);

  // Create tables
  // We use a junction table to handle the many-to-many relationship between cards and phones
  db.serialize(() => {
    db.run(`CREATE TABLE IF NOT EXISTS cards (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      card_number TEXT UNIQUE NOT NULL
    )`);
    db.run(`CREATE TABLE IF NOT EXISTS phones (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      phone_number TEXT UNIQUE NOT NULL
    )`);
    db.run(`CREATE TABLE IF NOT EXISTS associations (
      card_id INTEGER,
      phone_id INTEGER,
      PRIMARY KEY (card_id, phone_id),
      FOREIGN KEY (card_id) REFERENCES cards(id),
      FOREIGN KEY (phone_id) REFERENCES phones(id)
    )`);
  });

  // Helper to wrap db.get/all in promises
  const dbQuery = (query, params = []) => {
    return new Promise((resolve, reject) => {
      db.all(query, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  };

  const dbRun = (query, params = []) => {
    return new Promise((resolve, reject) => {
      db.run(query, params, function(err) {
        if (err) reject(err);
        else resolve(this);
      });
    });
  };

  // POST /associate_card
  app.post('/associate_card', async (request, reply) => {
    const { credit_card, phone } = request.body;

    if (!credit_card || !phone) {
      return reply.code(400).send({ error: 'Invalid request: credit_card and phone are required' });
    }

    try {
      // Insert card if not exists
      await dbRun(`INSERT OR IGNORE INTO cards (card_number) VALUES (?)`, [credit_card]);
      const cardRow = await dbQuery(`SELECT id FROM cards WHERE card_number = ?`, [credit_card]);
      const cardId = cardRow[0].id;

      // Insert phone if not exists
      await dbRun(`INSERT OR IGNORE INTO phones (phone_number) VALUES (?)`, [phone]);
      const phoneRow = await dbQuery(`SELECT id FROM phones WHERE phone_number = ?`, [phone]);
      const phoneId = phoneRow[0].id;

      // Create association
      await dbRun(`INSERT OR IGNORE INTO associations (card_id, phone_id) VALUES (?, ?)`, [cardId, phoneId]);

      return reply.code(201).send();
    } catch (err) {
      app.log.error(err);
      return reply.code(400).send({ error: 'Internal server error' });
    }
  });

  // POST /retrieve_cards
  app.post('/retrieve_cards', async (request, reply) => {
    const { phone_numbers } = request.body;

    if (!phone_numbers || !Array.isArray(phone_numbers) || phone_numbers.length === 0) {
      return reply.code(400).send({ error: 'Invalid request: phone_numbers array is required' });
    }

    try {
      /**
       * Logic: Find cards that are associated with ALL the provided phone numbers.
       * We group by card_id and count how many of the target phone numbers are associated.
       * If the count equals the length of the input array, the card matches all.
       */
      const placeholders = phone_numbers.map(() => '?').join(',');
      const query = `
        SELECT c.card_number 
        FROM cards c
        JOIN associations a ON c.id = a.card_id
        JOIN phones p ON p.id = a.phone_id
        WHERE p.phone_number IN (${placeholders})
        GROUP BY c.id
        HAVING COUNT(DISTINCT p.phone_number) = ?
      `;

      const rows = await dbQuery(query, [...phone_numbers, phone_numbers.length]);
      const cardNumbers = rows.map(row => row.card_number);

      if (cardNumbers.length === 0) {
        return reply.code(404).send({ error: 'Not found' });
      }

      return reply.code(200).send({ card_numbers: cardNumbers });
    } catch (err) {
      app.log.error(err);
      return reply.code(400).send({ error: 'Internal server error' });
    }
  });

  try {
    await app.listen({ port: PORT, hostname: HOST });
    console.log(`Server listening on ${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

start();