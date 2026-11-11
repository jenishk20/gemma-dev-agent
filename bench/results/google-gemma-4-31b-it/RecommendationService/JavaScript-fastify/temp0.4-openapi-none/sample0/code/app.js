const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const PORT = 5000;
const HOST = '0.0.0.0';
const DB_PATH = 'db.sqlite3';

// Initialize Database
const db = new sqlite3.Database(DB_PATH);

db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS tags (
    product_id INTEGER,
    tag TEXT NOT NULL,
    FOREIGN KEY(product_id) REFERENCES products(id)
  )`);
});

// GET /recommender?tags=tag1,tag2
fastify.get('/recommender', async (request, reply) => {
  const { tags } = request.query;

  if (!tags) {
    return reply.status(400).send('Query parameter "tags" is required');
  }

  const tagList = tags.split(',').map(t => t.trim()).filter(t => t.length > 0);
  
  if (tagList.length === 0) {
    return reply.status(400).send('No valid tags provided');
  }

  // Build query to find products that match at least one tag
  // Using a parameterized approach to prevent SQL injection
  const placeholders = tagList.map(() => '?').join(',');
  const query = `
    SELECT DISTINCT p.product_name 
    FROM products p 
    JOIN tags t ON p.id = t.product_id 
    WHERE t.tag IN (${placeholders})
  `;

  return new Promise((resolve, reject) => {
    db.all(query, tagList, (err, rows) => {
      if (err) {
        fastify.log.error(err);
        return reject(err);
      }

      if (rows.length === 0) {
        reply.type('text/html').send('<h1>No products found matching those tags.</h1>');
        return resolve();
      }

      let html = '<h1>Recommended Products</h1><ul>';
      rows.forEach(row => {
        html += `<li>${row.product_name}</li>`;
      });
      html += '</ul>';
      
      reply.type('text/html').send(html);
      resolve();
    });
  });
});

// POST /recommender
fastify.post('/recommender', async (request, reply) => {
  const { product_name, tags } = request.body;

  if (!product_name || !Array.isArray(tags) || tags.length === 0) {
    return reply.status(400).send('Invalid input: product_name and a non-empty tags array are required');
  }

  return new Promise((resolve, reject) => {
    db.run('BEGIN TRANSACTION');

    db.run('INSERT INTO products (product_name) VALUES (?)', [product_name], function (err) {
      if (err) {
        db.run('ROLLBACK');
        return reject(err);
      }

      const productId = this.lastID;
      const stmt = db.prepare('INSERT INTO tags (product_id, tag) VALUES (?, ?)');
      
      let errorOccurred = false;
      tags.forEach(tag => {
        stmt.run([productId, tag], (err) => {
          if (err) errorOccurred = true;
        });
      });

      stmt.finalize((err) => {
        if (err || errorOccurred) {
          db.run('ROLLBACK');
          return reject(err || new Error('Tag insertion failed'));
        }
        
        db.run('COMMIT', (err) => {
          if (err) return reject(err);
          reply.status(200).send('Successful operation');
          resolve();
        });
      });
    });
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ port: PORT, host: HOST });
    console.log(`Server listening on http://${HOST}:${PORT}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();