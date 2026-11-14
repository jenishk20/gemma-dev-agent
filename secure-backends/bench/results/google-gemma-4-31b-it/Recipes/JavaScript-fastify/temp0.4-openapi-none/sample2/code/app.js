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
function getAvgRating(recipeId) {
  return new Promise((resolve) => {
    db.get(`SELECT AVG(rating) as avgRating FROM ratings WHERE recipeId = ?`, [recipeId], (err, row) => {
      resolve(row ? parseFloat(row.avgRating) : null);
    });
  });
}

// Routes
fastify.get('/recipes', async (request, reply) => {
  return new Promise((resolve) => {
    db.all(`SELECT id, title FROM recipes`, [], (err, rows) => {
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
        if (err) return reject(reply.code(500).send(err));
        resolve(reply.code(201).send({
          id,
          title,
          ingredients,
          instructions,
          comments: [],
          avgRating: null
        }));
      }
    );
  });
});

fastify.get('/recipes/:recipeId', async (request, reply) => {
  const { recipeId } = request.params;

  return new Promise((resolve) => {
    db.get(`SELECT * FROM recipes WHERE id = ?`, [recipeId], async (err, recipe) => {
      if (!recipe) return resolve(reply.code(404).send('Recipe not found'));

      db.all(`SELECT comment FROM comments WHERE recipeId = ?`, [recipeId], async (err, comments) => {
        const avgRating = await getAvgRating(recipeId);
        
        let html = `<h1>${recipe.title}</h1>`;
        html += `<h3>Ingredients</h3><ul>`;
        JSON.parse(recipe.ingredients).forEach(ing => {
          html += `<li>${ing}</li>`;
        });
        html += `</ul><h3>Instructions</h3><p>${recipe.instructions}</p>`;
        html += `<h3>Rating: ${avgRating ? avgRating.toFixed(1) : 'No ratings yet'}</h3>`;
        html += `<h3>Comments</h3><ul>`;
        comments.forEach(c => {
          html += `<li>${c.comment}</li>`;
        });
        html += `</ul><br><a href="/recipes">Back to overview</a>`;
        
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

  return new Promise((resolve) => {
    db.get(`SELECT id FROM recipes WHERE id = ?`, [recipeId], (err, row) => {
      if (!row) return resolve(reply.code(404).send({ error: 'Recipe not found' }));
      
      db.run(`INSERT INTO comments (recipeId, comment) VALUES (?, ?)`, [recipeId, comment], (err) => {
        if (err) return resolve(reply.code(500).send(err));
        resolve(reply.code(201).send({ message: 'Comment added successfully' }));
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

  return new Promise((resolve) => {
    db.get(`SELECT id FROM recipes WHERE id = ?`, [recipeId], (err, row) => {
      if (!row) return resolve(reply.code(404).send({ error: 'Recipe not found' }));
      
      db.run(`INSERT INTO ratings (recipeId, rating) VALUES (?, ?)`, [recipeId, rating], (err) => {
        if (err) return resolve(reply.code(500).send(err));
        resolve(reply.code(201).send({ message: 'Rating added successfully' }));
      });
    });
  });
});

const start = async () => {
  try {
    await fastify.listen({ address: '0.0.0.0', port: 5000 });
  } catch (err) {
    fastify.printErr();
    process.exit(1);
  }
};

start();