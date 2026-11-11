import { Injectable, OnModuleInit } from '@nestjs/common';
import { open } from 'sqlite';
import sqlite3 from 'sqlite3';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

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
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
      );
      CREATE TABLE IF NOT EXISTS product_tags (
        product_id INTEGER,
        tag_id INTEGER,
        FOREIGN KEY(product_id) REFERENCES products(id),
        FOREIGN KEY(tag_id) REFERENCES tags(id),
        PRIMARY KEY(product_id, tag_id)
      );
    `);
  }

  async addProduct(productName: string, tags: string[]) {
    await this.db.run('BEGIN TRANSACTION');
    try {
      const productResult = await this.db.run('INSERT INTO products (product_name) VALUES (?)', [productName]);
      const productId = productResult.lastID;

      for (const tag of tags) {
        await this.db.run('INSERT OR IGNORE INTO tags (name) VALUES (?)', [tag]);
        const tagRow = await this.db.get('SELECT id FROM tags WHERE name = ?', [tag]);
        await this.db.run('INSERT INTO product_tags (product_id, tag_id) VALUES (?, ?)', [productId, tagRow.id]);
      }
      await this.db.run('COMMIT');
    } catch (e) {
      await this.db.run('ROLLBACK');
      throw e;
    }
  }

  async getProductsByTags(tagsQuery: string): Promise<any[]> {
    const tags = tagsQuery.split(',').map(t => t.trim()).filter(t => t !== '');
    if (tags.length === 0) return [];

    const placeholders = tags.map(() => '?').join(',');
    const query = `
      SELECT DISTINCT p.product_name 
      FROM products p
      JOIN product_tags pt ON p.id = pt.product_id
      JOIN tags t ON pt.tag_id = t.id
      WHERE t.name IN (${placeholders})
    `;

    return await this.db.all(query, tags);
  }
}