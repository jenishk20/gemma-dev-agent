const fastify = require('fastify');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = fastify({ logger: true });
const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
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
app.get('/recommender', async (request, reply) => {
  const { tags } = request.query;

  if (!tags) {
    return reply.status(400).send('Missing tags query parameter');
  }

  const tagList = tags.split(',').map(t => t.trim()).filter(t => t.length > 0);
  
  if (tagList.length === 0) {
    return reply.status(200).type('text/html').send('<h1>No tags provided</h1>');
  }

  // Build query to find products that match at least one tag
  const placeholders = tagList.map(() => '?').join(',');
  const query = `
    SELECT DISTINCT p.product_name 
    FROM products p 
    JOIN tags t ON p.id = t.product_id 
    WHERE t.tag IN (${placeholders})
  `;

  db.all(query, tagList, (err, rows) => {
    if (err) {
      reply.status(500).send(err.message);
      return;
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
  });
});

// POST /recommender
app.post('/recommender', async (request, reply) => {
  const { product_name, tags } = request.body;

  if (!product_name || !Array.isArray(tags)) {
    return reply.status(400).send('Invalid input: product_name and tags array are required');
  }

  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    
    const stmt = db.prepare('INSERT INTO products (product_name) VALUES (?)');
    stmt.run(product_name, function(err) {
      if (err) {
        db.run('ROLLBACK');
        return reply.status(500).send('Database error');
      }

      const productId = this.lastID;
      const tagStmt = db.prepare('INSERT INTO tags (product_id, tag) VALUES (?, ?)');
      
      tags.forEach(tag => {
        tagStmt.run(productId, tag);
      });

      tagStmt.finalize();
      db.run('COMMIT', (err) => {
        if (err) {
          reply.status(500).send('Commit error');
        } else {
          reply.status(200).send('Successful operation');
        }
      });
    });
    stmt.finalize();
  });
});

// Start server
const start = async () => {
  try {
    await app.listen({ address: '0.0.0.0', port: 5000 });
    console.log('Server listening on http://0.0.0.0:5000');
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
};

start();