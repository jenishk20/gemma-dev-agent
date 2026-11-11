import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;

  onModuleInit() {
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

  async getRecipesOverview(): Promise<any[]> {
    return new Promise((resolve, reject) => {
      this.db.all('SELECT id, title FROM recipes', (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  async createRecipe(data: { title: string, ingredients: string[], instructions: string }) {
    const id = uuidv4();
    const ingredientsJson = JSON.stringify(data.ingredients);
    return new Promise((resolve, reject) => {
      this.db.run(
        'INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)',
        [id, data.title, ingredientsJson, data.instructions],
        function(err) {
          if (err) reject(err);
          else resolve({ id, ...data });
        }
      );
    });
  }

  async getRecipeById(id: string) {
    return new Promise((resolve, reject) => {
      this.db.get('SELECT * FROM recipes WHERE id = ?', [id], (err, recipe) => {
        if (err) reject(err);
        if (!recipe) resolve(null);
        else {
          const ingredients = JSON.parse(recipe.ingredients);
          resolve({ ...recipe, ingredients });
        }
      });
    });
  }

  async getComments(recipeId: string) {
    return new Promise((resolve, reject) => {
      this.db.all('SELECT comment FROM comments WHERE recipeId = ?', [recipeId], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  async getAvgRating(recipeId: string) {
    return new Promise((resolve, reject) => {
      this.db.get('SELECT AVG(rating) as avgRating FROM ratings WHERE recipeId = ?', [recipeId], (err, row) => {
        if (err) reject(err);
        else resolve(row ? row.avgRating : null);
      });
    });
  }

  async addComment(recipeId: string, comment: string) {
    return new Promise((resolve, reject) => {
      this.db.run('INSERT INTO comments (recipeId, comment) VALUES (?, ?)', [recipeId, comment], (err) => {
        if (err) reject(err);
        else resolve(true);
      });
    });
  }

  async addRating(recipeId: string, rating: number) {
    return new Promise((resolve, reject) => {
      this.db.run('INSERT INTO ratings (recipeId, rating) VALUES (?, ?)', [recipeId, rating], (err) => {
        if (err) reject(err);
        else resolve(true);
      });
    });
  }
}