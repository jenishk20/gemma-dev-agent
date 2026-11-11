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

// Schema for /heartbeat POST
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

// Schema for /services POST
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
app.post('/heartbeat', { schema: heartbeatSchema }, async (request, reply) => {
  const { serviceId, token } = request.body;

  return new Promise((resolve, reject) => {
    const query = `
      INSERT INTO services (serviceId, token, lastNotification) 
      VALUES (?, ?, CURRENT_TIMESTAMP) 
      ON CONFLICT(serviceId) DO UPDATE SET 
        token = excluded.token, 
        lastNotification = CURRENT_TIMESTAMP
    `;
    
    db.run(query, [serviceId, token], function(err) {
      if (err) {
        app.log.error(err);
        reply.status(500).send({ error: 'Internal server error' });
        return resolve();
      }
      reply.status(200).send();
      resolve();
    });
  });
});

// Route: POST /services
app.post('/services', { schema: servicesSchema }, async (request, reply) => {
  const { token } = request.body;

  return new Promise((resolve, reject) => {
    const query = `SELECT serviceId, lastNotification FROM services WHERE token = ?`;
    
    db.all(query, [token], (err, rows) => {
      if (err) {
        app.log.error(err);
        reply.status(500).send({ error: 'Internal server error' });
        return resolve();
      }
      
      // Format the date to ISO string as per OpenAPI date-time format
      const result = rows.map(row => ({
        serviceId: row.serviceId,
        lastNotification: new Date(row.lastNotification).toISOString()
      }));
      
      reply.status(200).send(result);
      resolve();
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