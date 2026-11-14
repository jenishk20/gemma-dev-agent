const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');
const path = require('path');

const db = new sqlite3.Database('db.sqlite3');

// Initialize Database
db.serialize(() => {
  db.run(`CREATE TABLE IF NOT EXISTS recipes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipeId TEXT,
    comment TEXT NOT NULL,
    FOREIGN KEY(recipeId) REFERENCES recipes(id)
  )`);
  db.run(`CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipeId TEXT,
    rating INTEGER NOT NULL,
    FOREIGN KEY(recipeId) REFERENCES recipes(id)
  )`);
});

// Helper to calculate average rating
const getAvgRating = (recipeId) => {
  return new Promise((resolve) => {
    db.get(`SELECT AVG(rating) as avgRating FROM ratings WHERE recipeId = ?`, [recipeId], (err, row) => {
      resolve(row ? row.avgRating : null);
    });
  });
};

// Routes
fastify.get('/recipes', async (request, reply) => {
  return new Promise((resolve, reject) => {
    db.all(`SELECT id, title FROM recipes ORDER BY id DESC LIMIT 10`, [], (err, rows) => {
      if (err) return reject(err);
      
      let html = '<h1>Recipe Overview</h1><ul>';
      rows.forEach(row => {
        html += `<li><a href="/recipes/${row.id}">${row.title}</a></li>`;
      });
      html += '</ul>';
      
      reply.type('text/html').send(html);
      resolve();
    });
  });
});

fastify.post('/recipes/upload', async (request, reply) => {
  const { title, ingredients, instructions } = request.body;
  if (!title || !ingredients || !instructions) {
    return reply.code(400).send({ error: 'Invalid input' });
  }

  const id = uuidv4();
  const ingredientsStr = JSON.stringify(ingredients);

  return new Promise((resolve, reject) => {
    db.run(`INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)`, 
      [id, title, ingredientsStr, instructions], 
      function(err) {
        if (err) return reject(err);
        reply.code(201).send({
          id,
          title,
          ingredients,
          instructions,
          comments: [],
          avgRating: null
        });
        resolve();
      }
    );
  });
});

fastify.get('/recipes/:recipeId', async (request, reply) => {
  const { recipeId } = request.params;

  return new Promise((resolve, reject) => {
    db.get(`SELECT * FROM recipes WHERE id = ?`, [recipeId], async (err, recipe) => {
      if (err || !recipe) {
        return reply.code(404).send({ error: 'Recipe not found' }).send();
      }

      const avgRating = await getAvgRating(recipeId);
      
      db.all(`SELECT comment FROM comments WHERE recipeId = ?`, [recipeId], (err, comments) => {
        if (err) return reject(err);

        let html = `<h1>${recipe.title}</h1>`;
        html += `<p><strong>Ingredients:</strong> ${JSON.parse(recipe.ingredients).join(', ')}</p>`;
        html += `<p><strong>Instructions:</strong> ${recipe.instructions}</p>`;
        html += `<p><strong>Average Rating:</strong> ${avgRating ? avgRating.toFixed(1) : 'No ratings'}</p>`;
        
        html += `<h3>Comments</h3><ul>`;
        comments.forEach(c => {
          html += `<li>${c.comment}</li>`;
        });
        html += `</ul>`;
        
        html += `<hr><a href="/recipes">Back to overview</a>`;
        
        reply.type('text/html').send(html);
        resolve();
      });
    });
  });
});

fastify.post('/recipes/:recipeId/comments', async (request, reply) => {
  const { recipeId } = request.params;
  const { comment } = request.body;

  if (!comment) return reply.code(400).send({ error: 'Invalid input' });

  return new Promise((resolve, reject) => {
    db.get(`SELECT id FROM recipes WHERE id = ?`, [recipeId], (err, row) => {
      if (err || !row) return reply.code(404).send({ error: 'Recipe not found' }).send();
      
      db.run(`INSERT INTO comments (recipeId, comment) VALUES (?, ?)`, [recipeId, comment], function(err) {
        if (err) return reject(err);
        reply.code(201).send({ message: 'Comment added successfully' });
        resolve();
      });
    });
  });
});

fastify.post('/recipes/:recipeId/ratings', async (request, reply) => {
  const { recipeId } = request.params;
  const { rating } = request.body;

  if (rating === undefined || rating < 1 || rating > 5) {
    return reply.code(400).send({ error: 'Invalid input' });
  }

  return new Promise((resolve, reject) => {
    db.get(`SELECT id FROM recipes WHERE id = ?`, [recipeId], (err, row) => {
      if (err || !row) return reply.code(404).send({ error: 'Recipe not found' }).send();
      
      db.run(`INSERT INTO ratings (recipeId, rating) VALUES (?, ?)`, [recipeId, rating], function(err) {
        if (err) return reject(err);
        reply.code(201).send({ message: 'Rating added successfully' });
        resolve();
      });
    });
  });
});

// Start Server
const start = async () => {
  try {
    await fastify.listen({ port: 5000, host: '0.0.0.0' });
    console.log('Server is running on http://0.0.0.0:5000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();