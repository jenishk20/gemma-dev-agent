const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const dotenv = require('dotenv');

dotenv.config();

const app = express();
app.use(express.json());

const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  db.run(`
    CREATE TABLE IF NOT EXISTS services (
      serviceId TEXT PRIMARY KEY,
      token TEXT NOT NULL,
      lastNotification DATETIME DEFAULT CURRENT_TIMESTAMP
    )
  `);
});

/**
 * POST /heartbeat
 * Register a heartbeat for a service
 */
app.post('/heartbeat', (req, res) => {
  const { serviceId, token } = req.body;

  if (!serviceId || !token) {
    return res.status(400).json({ error: 'Invalid request payload. serviceId and token are required.' });
  }

  const now = new Date().toISOString();
  const sql = `
    INSERT INTO services (serviceId, token, lastNotification) 
    VALUES (?, ?, ?) 
    ON CONFLICT(serviceId) DO UPDATE SET 
      token = excluded.token, 
      lastNotification = excluded.lastNotification
  `;

  db.run(sql, [serviceId, token, now], function(err) {
    if (err) {
      console.error(err);
      return res.status(500).json({ error: 'Internal server error.' });
    }
    res.status(200).send('Heartbeat registered successfully.');
  });
});

/**
 * POST /services
 * Get overview of registered services matching the provided token
 */
app.post('/services', (req, res) => {
  const { token } = req.body;

  if (!token) {
    return res.status(400).json({ error: 'Invalid request payload. token is required.' });
  }

  const sql = `SELECT serviceId, lastNotification FROM services WHERE token = ?`;

  db.all(sql, [token], (err, rows) => {
    if (err) {
      console.error(err);
      return res.status(500).json({ error: 'Internal server error.' });
    }
    
    // Map results to ensure the format matches the OpenAPI schema
    const services = rows.map(row => ({
      serviceId: row.serviceId,
      lastNotification: row.lastNotification
    }));
    
    res.status(200).json(services);
  });
});

const PORT = 5000;
const HOST = '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Service Monitoring API listening at http://${HOST}:${PORT}`);
});