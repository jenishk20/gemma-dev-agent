const fastify = require('fastify')({ logger: true });
const sqlite3 = require('sqlite3').verbose();
const { v4: uuidv4 } = require('uuid');

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
    recipeId TEXT NOT NULL,
    comment TEXT NOT NULL,
    FOREIGN KEY(recipeId) REFERENCES recipes(id)
  )`);

  db.run(`CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipeId TEXT NOT NULL,
    rating INTEGER NOT NULL,
    FOREIGN KEY(recipeId) REFERENCES recipes(id)
  )`);
});

// Helper to get average rating
function calculateAvgRating(recipeId) {
  return new Promise((resolve, reject) => {
    db.get('SELECT AVG(rating) as avgRating FROM ratings WHERE recipeId = ?', [recipeId], (err, row) => {
      if (err) reject(err);
      resolve(row ? row.avgRating : null);
    });
  });
}

// Routes
fastify.get('/recipes', async (request, reply) => {
  return new Promise((resolve) => {
    db.all('SELECT id, title FROM recipes', [], (err, rows) => {
      if (err) {
        reply.status(500).send('Server Error');
        return resolve();
      }
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
    return reply.status(400).send({ error: 'Invalid input' });
  }

  const id = uuidv4();
  const ingredientsStr = JSON.stringify(ingredients);

  return new Promise((resolve) => {
    db.run('INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)', 
      [id, title, ingredientsStr, instructions], 
      function(err) {
        if (err) {
          reply.status(500).send({ error: 'Database error' });
          return resolve();
        }
        reply.status(201).send({
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

  return new Promise((resolve) => {
    db.get('SELECT * FROM recipes WHERE id = ?', [recipeId], async (err, recipe) => {
      if (err || !recipe) {
        reply.status(404).send('Recipe not found');
        return resolve();
      }

      const avgRating = await calculateAvgRating(recipeId);
      
      db.all('SELECT comment FROM comments WHERE recipeId = ?', [recipeId], (err, comments) => {
        const ingredients = JSON.parse(recipe.ingredients);
        
        let html = `<h1>${recipe.title}</h1>`;
        html += `<h3>Ingredients</h3><ul>`;
        ingredients.forEach(ing => html += `<li>${ing}</li>`);
        html += `</ul><h3>Instructions</h3><p>${recipe.instructions}</p>`;
        html += `<h3>Average Rating: ${avgRating ? avgRating.toFixed(1) : 'No ratings'}</h3>`;
        html += `<h3>Comments</h3><ul>`;
        comments.forEach(c => html += `<li>${c.comment}</li>`);
        html += `</ul>`;
        html += `<hr><a href="/recipes">Back to Overview</a>`;
        
        reply.type('text/html').send(html);
        resolve();
      });
    });
  });
});

fastify.post('/recipes/:recipeId/comments', async (request, reply) => {
  const { recipeId } = request.params;
  const { comment } = request.body;

  if (!comment) return reply.status(400).send({ error: 'Invalid input' });

  return new Promise((resolve) => {
    db.get('SELECT id FROM recipes WHERE id = ?', [recipeId], (err, row) => {
      if (err || !row) {
        reply.status(404).send({ error: 'Recipe not found' });
        return resolve();
      }
      db.run('INSERT INTO comments (recipeId, comment) VALUES (?, ?)', [recipeId, comment], (err) => {
        if (err) {
          reply.status(500).send({ error: 'Database error' });
        } else {
          reply.status(201).send({ message: 'Comment added successfully' });
        }
        resolve();
      });
    });
  });
});

fastify.post('/recipes/:recipeId/ratings', async (request, reply) => {
  const { recipeId } = request.params;
  const { rating } = request.body;

  if (rating === undefined || rating < 1 || rating > 5) {
    return reply.status(400).send({ error: 'Invalid input' });
  }

  return new Promise((resolve) => {
    db.get('SELECT id FROM recipes WHERE id = ?', [recipeId], (err, row) => {
      if (err || !row) {
        reply.status(404).send({ error: 'Recipe not found' });
        return resolve();
      }
      db.run('INSERT INTO ratings (recipeId, rating) VALUES (?, ?)', [recipeId, rating], (err) => {
        if (err) {
          reply.status(500).send({ error: 'Database error' });
        } else {
          reply.status(201).send({ message: 'Rating added successfully' });
        }
        resolve();
      });
    });
  });
});

const start = async () => {
  try {
    await fastify.listen({ host: '0.0.0.0', port: 5000 });
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();