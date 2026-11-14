import { Injectable, OnModuleInit } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    
    const run = promisify(this.db.run.bind(this.db));
    
    // Create tables for products and tags (Many-to-Many relationship)
    await run(`CREATE TABLE IF NOT EXISTS products (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL
    )`);
    
    await run(`CREATE TABLE IF NOT EXISTS tags (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT UNIQUE NOT NULL
    )`);
    
    await run(`CREATE TABLE IF NOT EXISTS product_tags (
      product_id INTEGER,
      tag_id INTEGER,
      FOREIGN KEY(product_id) REFERENCES products(id),
      FOREIGN KEY(tag_id) REFERENCES tags(id),
      PRIMARY KEY(product_id, tag_id)
    )`);
  }

  async addProduct(name: string, tags: string[]) {
    const run = promisify(this.db.run.bind(this.db));
    const get = promisify(this.db.get.bind(this.db));

    // Insert product
    await run('INSERT INTO products (name) VALUES (?)', [name]);
    const product = await get('SELECT last_insert_rowid() as id');
    const productId = product.id;

    for (const tag of tags) {
      // Ensure tag exists
      await run('INSERT OR IGNORE INTO tags (name) VALUES (?)', [tag]);
      const tagRow = await get('SELECT id FROM tags WHERE name = ?', [tag]);
      
      // Link product to tag
      await run('INSERT OR IGNORE INTO product_tags (product_id, tag_id) VALUES (?, ?)', [productId, tagRow.id]);
    }
  }

  async getProductsByTags(tagsQuery: string): Promise<any[]> {
    const all = promisify(this.db.all.bind(this.db));
    const searchTags = tagsQuery.split(',').map(t => t.trim());

    // Query to find products that match at least one of the tags
    const sql = `
      SELECT DISTINCT p.name 
      FROM products p
      JOIN product_tags pt ON p.id = pt.product_id
      JOIN tags t ON pt.tag_id = t.id
      WHERE t.name IN (${searchTags.map(() => '?').join(',')})
    `;

    return await all(sql, searchTags);
  }
}