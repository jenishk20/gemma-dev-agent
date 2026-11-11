import { Injectable, OnModuleInit, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;
  private run = promisify(this.db?.run.bind(this.db));
  private get = promisify(this.db?.get.bind(this.db));
  private all = promisify(this.db?.all.bind(this.db));

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    
    // Re-bind promisified methods after db is initialized
    this.run = promisify(this.db.run.bind(this.db));
    this.get = promisify(this.db.get.bind(this.db));
    this.all = promisify(this.db.all.bind(this.db));

    await this.run(`
      CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        data TEXT
      )
    `);
  }

  async addProduct(product: Record<string, any>) {
    if (!product.name) {
      throw new BadRequestException('Product name is required');
    }
    
    // We store the entire object as a JSON string to handle unstructured properties
    const dataString = JSON.stringify(product);
    try {
      await this.run('INSERT INTO products (name, data) VALUES (?, ?)', [product.name, dataString]);
    } catch (err) {
      throw new BadRequestException('Product already exists or database error');
    }
  }

  async downloadProduct(name: string) {
    const row = await this.get('SELECT data FROM products WHERE name = ?', [name]);
    if (!row) {
      throw new BadRequestException('Product not found');
    }
    return { data: row.data };
  }

  async uploadProduct(name: string, data: string) {
    // Validate that data is a valid JSON string representing the product
    try {
      JSON.parse(data);
    } catch (e) {
      throw new BadRequestException('Invalid data format');
    }

    await this.run('INSERT OR REPLACE INTO products (name, data) VALUES (?, ?)', [name, data]);
  }

  async searchProducts(query: string) {
    // Search in the JSON blob for the query string
    // This matches the name or any value within the unstructured properties
    const rows = await this.all('SELECT data FROM products WHERE data LIKE ?', [`%${query}%`]);
    
    const results = rows.map(row => JSON.parse(row.data));
    return { results };
  }
}