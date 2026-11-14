import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import { open } from 'sqlite';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS recipes (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        ingredients TEXT NOT NULL,
        instructions TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipeId TEXT,
        comment TEXT NOT NULL,
        FOREIGN KEY(recipeId) REFERENCES recipes(id)
      );
      CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipeId TEXT,
        rating INTEGER NOT NULL,
        FOREIGN KEY(recipeId) REFERENCES recipes(id)
      );
    `);
  }

  async getRecipesOverview() {
    const recipes = await this.db.all('SELECT id, title FROM recipes');
    let html = '<h1>Recipe Overview</h1><ul>';
    recipes.forEach(r => {
      html += `<li><a href="/recipes/${r.id}">${r.title}</a></li>`;
    });
    html += '</ul>';
    return html;
  }

  async uploadRecipe(data: { title: string, ingredients: string[], instructions: string }) {
    const id = uuidv4();
    const ingredientsJson = JSON.stringify(data.ingredients);
    await this.db.run(
      'INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)',
      [id, data.title, ingredientsJson, data.instructions]
    );
    return { id, ...data };
  }

  async getRecipeById(id: string) {
    const recipe = await this.db.get('SELECT * FROM recipes WHERE id = ?', [id]);
    if (!recipe) throw new NotFoundException('Recipe not found');

    const comments = await this.db.all('SELECT comment FROM comments WHERE recipeId = ?', [id]);
    const ratings = await this.db.all('SELECT rating FROM ratings WHERE recipeId = ?', [id]);

    const avgRating = ratings.length > 0 
      ? ratings.reduce((acc, curr) => acc + curr.rating, 0) / ratings.length 
      : null;

    const ingredients = JSON.parse(recipe.ingredients);

    // Returning HTML as per OpenAPI spec
    let html = `<h1>${recipe.title}</h1>`;
    html += `<h3>Ingredients</h3><ul>`;
    ingredients.forEach(ing => html += `<li>${ing}</li>`);
    html += `</ul><h3>Instructions</h3><p>${recipe.instructions}</p>`;
    html += `<h3>Average Rating: ${avgRating !== null ? avgRating.toFixed(1) : 'No ratings'}</h3>`;
    html += `<h3>Comments</h3><ul>`;
    comments.forEach(c => html += `<li>${c.comment}</li>`);
    html += `</ul>`;

    return html;
  }

  async addComment(recipeId: string, comment: string) {
    const recipe = await this.db.get('SELECT id FROM recipes WHERE id = ?', [recipeId]);
    if (!recipe) throw new NotFoundException('Recipe not found');
    
    await this.db.run('INSERT INTO comments (recipeId, comment) VALUES (?, ?)', [recipeId, comment]);
    return { message: 'Comment added successfully' };
  }

  async addRating(recipeId: string, rating: number) {
    const recipe = await this.db.get('SELECT id FROM recipes WHERE id = ?', [recipeId]);
    if (!recipe) throw new NotFoundException('Recipe not found');

    if (rating < 1 || rating > 5) throw new Error('Rating must be between 1 and 5');

    await this.db.run('INSERT INTO ratings (recipeId, rating) VALUES (?, ?)', [recipeId, rating]);
    return { message: 'Rating added successfully' };
  }
}