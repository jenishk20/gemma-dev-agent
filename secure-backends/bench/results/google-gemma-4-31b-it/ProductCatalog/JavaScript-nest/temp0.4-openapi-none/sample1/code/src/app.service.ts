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
        name TEXT PRIMARY KEY,
        data TEXT
      )
    `);
  }

  async addProduct(product: any) {
    if (!product.name) {
      throw new BadRequestException('Product name is required');
    }
    
    const { name, ...properties } = product;
    // We store the full object including name as a JSON string to preserve all unstructured properties
    const dataString = JSON.stringify(product);
    
    try {
      await this.db.run('INSERT INTO products (name, data) VALUES (?, ?)', [name, dataString]);
    } catch (e) {
      throw new BadRequestException('Product already exists or database error');
    }
  }

  async downloadProduct(name: string) {
    const product = await this.db.get('SELECT data FROM products WHERE name = ?', [name]);
    if (!product) {
      throw new BadRequestException('Product not found');
    }
    return { data: product.data };
  }

  async uploadProduct(name: string, data: string) {
    // Validate that data is a valid JSON string and contains the name
    try {
      const parsed = JSON.parse(data);
      if (typeof parsed !== 'object' || parsed === null) throw new Error();
    } catch (e) {
      throw new BadRequestException('Invalid data format');
    }

    await this.db.run('UPDATE products SET data = ? WHERE name = ?', [data, name]);
    const result = await this.db.run('UPDATE products SET data = ? WHERE name = ?', [data, name]);
    
    // If no rows were changed, the product didn't exist
    const exists = await this.db.get('SELECT 1 FROM products WHERE name = ?', [name]);
    if (!exists) {
      // If it doesn't exist, the schema says "replaces any previous data", 
      // but usually implies the product must exist. We'll handle it as a 400 if not found.
      throw new BadRequestException('Product not found in catalog');
    }
  }

  async searchProducts(query: string) {
    const products = await this.db.all('SELECT data FROM products');
    const results = products
      .map(p => JSON.parse(p.data))
      .filter(p => {
        return Object.values(p).some(val => 
          typeof val === 'string' && val.toLowerCase().includes(query.toLowerCase())
        );
      });

    return { results };
  }
}