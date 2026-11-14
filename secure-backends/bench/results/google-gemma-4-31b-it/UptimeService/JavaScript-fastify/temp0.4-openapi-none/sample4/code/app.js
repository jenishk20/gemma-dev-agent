const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Database initialization
const db = new sqlite3.Database('db.sqlite3');

db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS services (
      serviceId TEXT PRIMARY KEY,
      token TEXT NOT NULL,
      lastNotification DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
});

// Validation schemas for Fastify
const heartbeatSchema = {
  body: {
    type: 'object',
    required: ['serviceId', 'token'],
    properties: {
      serviceId: { type: 'string' },
      token: { type: 'string' }
    }
  }
};

const servicesSchema = {
  body: {
    type: 'object',
    required: ['token'],
    properties: {
      token: { type: 'string' }
    }
  }
};

// Route: POST /heartbeat
fastify.post('/heartbeat', { schema: heartbeatSchema }, async (request, reply) => {
  const { serviceId, token } = request.body;

  return new Promise((resolve, reject) => {
    const query = `
      INSERT INTO services (serviceId, token, lastNotification) 
      VALUES (?, ?, CURRENT_TIMESTAMP) 
      ON CONFLICT(serviceId) DO UPDATE SET 
        token = excluded.token, 
        lastNotification = CURRENT_TIMESTAMP
    `;

    db.run(query, [serviceId, token], function (err) {
      if (err) {
        fastify.log.error(err);
        return resolve(reply.status(500).send({ error: 'Internal server error' }));
      }
      resolve(reply.status(200).send());
    });
  });
});

// Route: POST /services
fastify.post('/services', { schema: servicesSchema }, async (request, reply) => {
  const { token } = request.body;

  return new Promise((resolve, reject) => {
    const query = `SELECT serviceId, lastNotification FROM services WHERE token = ?`;

    db.all(query, [token], (err, rows) => {
      if (err) {
        fastify.log.error(err);
        return resolve(reply.status(500).send({ error: 'Internal server error' }));
      }

      // Format the date to ISO string to match date-time format
      const formattedRows = rows.map(row => ({
        serviceId: row.serviceId,
        lastNotification: new Date(row.lastNotification).toISOString()
      }));

      resolve(reply.status(200).send(formattedRows));
    });
  });
});

// Start server
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