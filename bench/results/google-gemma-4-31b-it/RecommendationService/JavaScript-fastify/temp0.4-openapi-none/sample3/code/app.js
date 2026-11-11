const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

// Initialize SQLite Database
const db = new sqlite3.Database('db.sqlite3');

// Create tables
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
  const { tags: tagsQuery } = request.query;

  if (!tagsQuery) {
    return reply.status(400).send('Missing required query parameter: tags');
  }

  const searchTags = tagsQuery.split(',').map(t => t.trim()).filter(t => t.length > 0);
  
  if (searchTags.length === 0) {
    return reply.status(200).type('text/html').send('<h1>No products found</h1>');
  }

  return new Promise((resolve, reject) => {
    // Find products that match at least one of the provided tags
    const placeholders = searchTags.map(() => '?').join(',');
    const sql = `
      SELECT DISTINCT p.product_name 
      FROM products p 
      JOIN tags t ON p.id = t.product_id 
      WHERE t.tag IN (${placeholders})
    `;

    db.all(sql, searchTags, (err, rows) => {
      if (err) {
        fastify.log.error(err);
        return reject(err);
      }

      let html = '<html><body><h1>Recommended Products</h1><ul>';
      if (rows.length === 0) {
        html += '<li>No products found matching those tags.</li>';
      } else {
        rows.forEach(row => {
          html += `<li>${row.product_name}</li>`;
        });
      }
      html += '</ul></body></html>';
      
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
    db.serialize(() => {
      db.run('BEGIN TRANSACTION');

      const stmtProduct = db.prepare('INSERT INTO products (product_name) VALUES (?)');
      stmtProduct.run(product_name, function(err) {
        if (err) {
          db.run('ROLLBACK');
          return reject(err);
        }

        const productId = this.lastID;
        const stmtTag = db.prepare('INSERT INTO tags (product_id, tag) VALUES (?, ?)');
        
        let tagError = false;
        tags.forEach(tag => {
          stmtTag.run(productId, tag, (err) => {
            if (err) tagError = true;
          });
        });

        stmtTag.finalize();
        stmtProduct.finalize();

        if (tagError) {
          db.run('ROLLBACK');
          return reject(new Error('Failed to insert tags'));
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
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();