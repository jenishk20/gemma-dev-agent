const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const DB_PATH = 'db.sqlite3';
const PORT = 5000;
const HOST = '0.0.0.0';

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

// GET /recommender
fastify.get('/recommender', async (request, reply) => {
  const { tags } = request.query;

  if (!tags) {
    reply.code(400).send('Missing tags query parameter');
    return;
  }

  const tagList = tags.split(',').map(t => t.trim()).filter(t => t !== '');
  if (tagList.length === 0) {
    reply.code(400).send('No valid tags provided');
    return;
  }

  // Use placeholders for the IN clause to prevent SQL injection
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
        request.log.error(err);
        reply.code(500).send('Internal Server Error');
        return resolve();
      }

      let html = '<h1>Recommended Products</h1>';
      if (rows.length === 0) {
        html += '<p>No products found matching those tags.</p>';
      } else {
        html += '<ul>';
        rows.forEach(row => {
          html += `<li>${row.product_name}</li>`;
        });
        html += '</ul>';
      }
      
      reply.type('text/html').send(html);
      resolve();
    });
  });
});

// POST /recommender
fastify.post('/recommender', async (request, reply) => {
  const { product_name, tags } = request.body;

  if (!product_name || !Array.isArray(tags) || tags.length === 0) {
    reply.code(400).send('Invalid input: product_name and a non-empty tags array are required');
    return;
  }

  return new Promise((resolve, reject) => {
    db.serialize(() => {
      db.run('BEGIN TRANSACTION');

      const stmtProduct = db.prepare('INSERT INTO products (product_name) VALUES (?)');
      stmtProduct.run(product_name, function(err) {
        if (err) {
          db.run('ROLLBACK');
          reply.code(500).send('Database error');
          return resolve();
        }

        const productId = this.lastID;
        const stmtTag = db.prepare('INSERT INTO tags (product_id, tag) VALUES (?, ?)');
        
        let errorOccurred = false;
        tags.forEach(tag => {
          stmtTag.run(productId, tag, (err) => {
            if (err) errorOccurred = true;
          });
        });

        stmtTag.finalize();

        if (errorOccurred) {
          db.run('ROLLBACK');
          reply.code(500).send('Database error while inserting tags');
        } else {
          db.run('COMMIT', (err) => {
            if (err) {
              reply.code(500).send('Commit error');
            } else {
              reply.code(200).send('Successful operation');
            }
          });
        }
        resolve();
      });
      stmtProduct.finalize();
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