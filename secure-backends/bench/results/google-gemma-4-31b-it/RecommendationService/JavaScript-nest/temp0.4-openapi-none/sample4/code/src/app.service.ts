import { Injectable, OnModuleInit } from '@nestjs/common';
import { open, Database } from 'sqlite';
import * as sqlite3 from 'sqlite3';

@Injectable()
export class AppService implements OnModuleInit {
  private db: Database;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS tags (
        product_id INTEGER,
        tag TEXT NOT NULL,
        FOREIGN KEY(product_id) REFERENCES products(id)
      );
    `);
  }

  async addProduct(productName: string, tags: string[]) {
    const result = await this.db.run(
      'INSERT INTO products (product_name) VALUES (?)',
      [productName],
    );
    const productId = result.lastID;

    const tagStatements = tags.map(tag => 
      this.db.run('INSERT INTO tags (product_id, tag) VALUES (?, ?)', [productId, tag])
    );
    await Promise.all(tagStatements);
  }

  async getProductsByTags(tagsQuery: string): Promise<any[]> {
    const searchTags = tagsQuery.split(',').map(t => t.trim()).filter(t => t.length > 0);
    if (searchTags.length === 0) return [];

    // Find products that match at least one of the tags
    const placeholders = searchTags.map(() => '?').join(',');
    const query = `
      SELECT DISTINCT p.product_name 
      FROM products p 
      JOIN tags t ON p.id = t.product_id 
      WHERE t.tag IN (${placeholders})
    `;
    
    return await this.db.all(query, searchTags);
  }
}