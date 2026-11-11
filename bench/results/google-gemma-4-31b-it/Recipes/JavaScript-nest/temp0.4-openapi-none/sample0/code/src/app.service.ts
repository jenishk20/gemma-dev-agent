import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import { open } from 'sqlite';
import sqlite3 from 'sqlite3';
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

  async getAllRecipesSummary() {
    return await this.db.all('SELECT id, title FROM recipes');
  }

  async createRecipe(recipeData: { title: string; ingredients: string[]; instructions: string }) {
    const id = uuidv4();
    const ingredientsJson = JSON.stringify(recipeData.ingredients);
    await this.db.run(
      'INSERT INTO recipes (id, title, ingredients, instructions) VALUES (?, ?, ?, ?)',
      [id, recipeData.title, ingredientsJson, recipeData.instructions],
    );
    return { id, ...recipeData };
  }

  async getRecipeById(id: string) {
    const recipe = await this.db.get('SELECT * FROM recipes WHERE id = ?', [id]);
    if (!recipe) throw new NotFoundException('Recipe not found');

    const comments = await this.db.all('SELECT comment FROM comments WHERE recipeId = ?', [id]);
    const ratings = await this.db.all('SELECT rating FROM ratings WHERE recipeId = ?', [id]);

    const avgRating = ratings.length > 0 
      ? ratings.reduce((acc, curr) => acc + curr.rating, 0) / ratings.length 
      : null;

    return {
      ...recipe,
      ingredients: JSON.parse(recipe.ingredients),
      comments,
      avgRating,
    };
  }

  async addComment(recipeId: string, commentText: string) {
    const recipe = await this.db.get('SELECT id FROM recipes WHERE id = ?', [recipeId]);
    if (!recipe) throw new NotFoundException('Recipe not found');
    
    await this.db.run('INSERT INTO comments (recipeId, comment) VALUES (?, ?)', [recipeId, commentText]);
  }

  async addRating(recipeId: string, rating: number) {
    const recipe = await this.db.get('SELECT id FROM recipes WHERE id = ?', [recipeId]);
    if (!recipe) throw new NotFoundException('Recipe not found');

    await this.db.run('INSERT INTO ratings (recipeId, rating) VALUES (?, ?)', [recipeId, rating]);
  }
}