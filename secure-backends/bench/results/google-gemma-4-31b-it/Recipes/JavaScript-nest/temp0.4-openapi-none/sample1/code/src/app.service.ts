import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    this.initDb();
  }

  private initDb() {
    this.db.serialize(() => {
      this.db.run(`CREATE TABLE IF NOT EXISTS recipes (
        id TEXT PRIMARY KEY,
        title TEXT,
        ingredients TEXT,
        instructions TEXT
      )`);
      this.db.run(`CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipeId TEXT,
        comment TEXT,
        FOREIGN KEY(recipeId) REFERENCES recipes(id)
      )`);
      this.db.run(`CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipeId TEXT,
        rating INTEGER,
        FOREIGN KEY(recipeId) REFERENCES recipes(id)
      )`);
    });
  }

  async getRecipesOverview(): Promise<string> {
    return new Promise((resolve, reject) => {
      this.db.all('SELECT id, title FROM recipes', [], (err, rows) => {
        if (err) return reject(err);
        let html = '<h1>Recipe Overview</h1><ul>';
        rows.forEach(row => {
          html += `<li><a href="/recipes/${row.id}">${row.title}</a></li>`;
        });
        html += '</ul>';
        resolve(html);
      });
    });
  }

  async createRecipe(data: { title: string, ingredients: string[], instructions: string }) {
    const id = uuidv4();
    const ingredientsJson = JSON.stringify(data.ingredients);
    
    return new Promise<any>((resolve, reject) => {
      this.db.run(
        'INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)',
        [id, data.title, ingredientsJson, data.instructions],
        function(err) {
          if (err) return reject(err);
          resolve({ id, ...data });
        }
      );
    });
  }

  async getRecipeById(id: string): Promise<string> {
    return new Promise((resolve, reject) => {
      this.db.get('SELECT * FROM recipes WHERE id = ?', [id], (err, recipe) => {
        if (err || !recipe) return reject(new NotFoundException('Recipe not found'));

        this.db.all('SELECT comment FROM comments WHERE recipeId = ?', [id], (errC, comments) => {
          this.db.all('SELECT rating FROM ratings WHERE recipeId = ?', [id], (errR, ratings) => {
            const avgRating = ratings.length > 0 
              ? ratings.reduce((acc, curr) => acc + curr.rating, 0) / ratings.length 
              : null;

            let html = `<h1>${recipe.title}</h1>`;
            html += `<h3>Ingredients</h3><p>${JSON.parse(recipe.ingredients).join(', ')}</p>`;
            html += `<h3>Instructions</h3><p>${recipe.instructions}</p>`;
            html += `<p><strong>Average Rating:</strong> ${avgRating || 'No ratings yet'}</p>`;
            html += `<h3>Comments</h3><ul>`;
            comments.forEach(c => html += `<li>${c.comment}</li>`);
            html += `</ul><a href="/recipes">Back to overview</a>`;
            
            resolve(html);
          });
        });
      });
    });
  }

  async addComment(recipeId: string, comment: string) {
    return new Promise((resolve, reject) => {
      this.db.get('SELECT id FROM recipes WHERE id = ?', [recipeId], (err, row) => {
        if (err || !row) return reject(new NotFoundException('Recipe not found'));
        this.db.run('INSERT INTO comments (recipeId, comment) VALUES (?, ?)', [recipeId, comment], (err) => {
          if (err) return reject(err);
          resolve({ success: true });
        });
      });
    });
  }

  async addRating(recipeId: string, rating: number) {
    return new Promise((resolve, reject) => {
      this.db.get('SELECT id FROM recipes WHERE id = ?', [recipeId], (err, row) => {
        if (err || !row) return reject(new NotFoundException('Recipe not found'));
        this.db.run('INSERT INTO ratings (recipeId, rating) VALUES (?, ?)', [recipeId, rating], (err) => {
          if (err) return reject(err);
          resolve({ success: true });
        });
      });
    });
  }
}