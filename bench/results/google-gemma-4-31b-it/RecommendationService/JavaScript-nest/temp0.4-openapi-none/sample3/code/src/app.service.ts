import { Injectable, OnModuleInit, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { open } from 'sqlite';

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
      CREATE TABLE IF NOT EXISTS product_tags (
        product_id INTEGER,
        tag TEXT,
        FOREIGN KEY(product_id) REFERENCES products(id)
      );
      CREATE INDEX IF NOT EXISTS idx_tags ON product_tags(tag);
    `);
  }

  async addProduct(productName: string, tags: string[]) {
    if (!productName || !tags || !Array.isArray(tags) || tags.length === 0) {
      throw new BadRequestException('Invalid input: product_name and tags are required');
    }

    const result = await this.db.run('INSERT INTO products (product_name) VALUES (?)', [productName]);
    const productId = result.lastID;

    const stmt = await this.db.prepare('INSERT INTO product_tags (product_id, tag) VALUES (?, ?)');
    for (const tag of tags) {
      await stmt.run(productId, tag.toLowerCase().trim());
    }
    await stmt.finalize();

    return { success: true };
  }

  async getRecommendations(tagsQuery: string): Promise<string> {
    const tags = tagsQuery.split(',').map(t => t.toLowerCase().trim()).filter(t => t !== '');
    
    if (tags.length === 0) {
      return '<h1>No tags provided</h1>';
    }

    // Query to find products that match at least one of the provided tags
    const placeholders = tags.map(() => '?').join(',');
    const query = `
      SELECT DISTINCT p.product_name 
      FROM products p 
      JOIN product_tags pt ON p.id = pt.product_id 
      WHERE pt.tag IN (${placeholders})
    `;

    const products = await this.db.all(query, tags);

    if (products.length === 0) {
      return '<h1>No products found matching these tags</h1>';
    }

    let html = '<h1>Recommended Products</h1><ul>';
    products.forEach(p => {
      html += `<li>${p.product_name}</li>`;
    });
    html += '</ul>';

    return html;
  }
}