const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const PORT = 5000;
const HOST = '0.0.0.0';
const DB_PATH = path.join(__dirname, 'db.sqlite3');

// Initialize Database
const db = new sqlite3.Database(DB_PATH);

db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS services (
      serviceId TEXT PRIMARY KEY,
      token TEXT NOT NULL,
      lastNotification DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
});

const app = fastify({ logger: true });

// Heartbeat Route
app.post('/heartbeat', async (request, reply) => {
  const { serviceId, token } = request.body;

  if (!serviceId || !token) {
    return reply.status(400).send({ error: 'Invalid request payload' });
  }

  try {
    const now = new Date().toISOString();
    // Upsert: Insert or Update the last notification date and token
    db.run(
      `INSERT INTO services (serviceId, token, lastNotification) 
       VALUES (?, ?, ?) 
       ON CONFLICT(serviceId) DO UPDATE SET 
       token = excluded.token, 
       lastNotification = excluded.lastNotification`,
      [serviceId, token, now],
      (err) => {
        if (err) {
          reply.status(500).send({ error: 'Internal server error' });
        } else {
          reply.status(200).send({ message: 'Heartbeat registered successfully' });
        }
      }
    );
  } catch (error) {
    reply.status(500).send({ error: 'Internal server error' });
  }
});

// Services Overview Route
app.post('/services', async (request, reply) => {
  const { token } = request.body;

  if (!token) {
    return reply.status(400).send({ error: 'Invalid request payload' });
  }

  try {
    db.all(
      `SELECT serviceId, lastNotification FROM services WHERE token = ?`,
      [token],
      (err, rows) => {
        if (err) {
          reply.status(500).send({ error: 'Internal server error' });
        } else {
          reply.status(200).send(rows);
        }
      }
    );
  } catch (error) {
    reply.status(500).send({ error: 'Internal server error' });
  }
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