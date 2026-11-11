const Koa = require('koa');
const Router = require('koa-router');
const bodyParser = require('koa-bodyparser');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = new Koa();
const router = new Router();
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
router.get('/recommender', async (ctx) => {
  const tagsQuery = ctx.query.tags;
  if (!tagsQuery) {
    ctx.throw(400, 'Missing required query parameter: tags');
  }

  const searchTags = tagsQuery.split(',').map(t => t.trim()).filter(t => t.length > 0);
  
  if (searchTags.length === 0) {
    ctx.type = 'text/html';
    ctx.body = '<h1>No products found</h1>';
    return;
  }

  // Use placeholders to prevent SQL injection
  const placeholders = searchTags.map(() => '?').join(',');
  const sql = `
    SELECT DISTINCT p.product_name 
    FROM products p 
    JOIN tags t ON p.id = t.product_id 
    WHERE t.tag IN (${placeholders})
  `;

  db.all(sql, searchTags, (err, rows) => {
    if (err) {
      ctx.throw(500, err.message);
    }

    let html = '<html><body>';
    html += '<h1>Recommended Products</h1>';
    if (rows.length === 0) {
      html += '<p>No products match the provided tags.</p>';
    } else {
      html += '<ul>';
      rows.forEach(row => {
        html += `<li>${row.product_name}</li>`;
      });
      html += '</ul>';
    }
    html += '</body></html>';
    
    ctx.type = 'text/html';
    ctx.body = html;
  });
});

// POST /recommender
router.post('/recommender', async (ctx) => {
  const { product_name, tags } = ctx.request.body;

  if (!product_name || !Array.isArray(tags)) {
    ctx.status = 400;
    ctx.body = 'Invalid input: product_name and tags (array) are required';
    return;
  }

  db.serialize(() => {
    db.run('BEGIN TRANSACTION');
    
    const stmt = db.prepare('INSERT INTO products (product_name) VALUES (?)');
    stmt.run(product_name, function(err) {
      if (err) {
        db.run('ROLLBACK');
        ctx.status = 500;
        ctx.body = 'Database error';
        return;
      }
      
      const productId = this.lastID;
      const tagStmt = db.prepare('INSERT INTO tags (product_id, tag) VALUES (?, ?)');
      
      try {
        tags.forEach(tag => {
          tagStmt.run(productId, tag);
        });
        tagStmt.finalize();
        db.run('COMMIT');
        ctx.status = 200;
        ctx.body = 'Successful operation';
      } catch (e) {
        db.run('ROLLBACK');
        ctx.status = 500;
        ctx.body = 'Error inserting tags';
      }
    });
    stmt.finalize();
  });
});

app.use(bodyParser());
app.use(router.routes()).use(router.allowedMethods());

app.listen(5000, '0.0.0.0', () => {
  console.log('Server running on http://0.0.0.0:5000');
});