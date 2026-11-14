import { Injectable, OnModuleInit } from '@nestjs/common';
import { open } from 'sqlite';
import * as sqlite3 from 'sqlite3';

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
        name TEXT NOT NULL
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
    const product = await this.db.run('INSERT INTO products (name) VALUES (?)', [productName]);
    const productId = product.lastID;

    for (const tag of tags) {
      await this.db.run('INSERT OR IGNORE INTO tags (name) VALUES (?)', [tag]);
      const tagRow = await this.db.get('SELECT id FROM tags WHERE name = ?', [tag]);
      await this.db.run('INSERT INTO product_tags (product_id, tag_id) VALUES (?, ?)', [productId, tagRow.id]);
    }
  }

  async getProductsByTags(tagsQuery: string): Promise<any[]> {
    const tagsList = tagsQuery.split(',').map(t => t.trim()).filter(t => t !== '');
    if (tagsList.length === 0) return [];

    const placeholders = tagsList.map(() => '?').join(',');
    const query = `
      SELECT DISTINCT p.name 
      FROM products p
      JOIN product_tags pt ON p.id = pt.product_id
      JOIN tags t ON pt.tag_id = t.id
      WHERE t.name IN (${placeholders})
    `;

    return await this.db.all(query, tagsList);
  }
}