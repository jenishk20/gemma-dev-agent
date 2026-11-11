import { Injectable, OnModuleInit, BadRequestException } from '@nestjs/common';
import sqlite3 from 'sqlite3';
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
        properties TEXT
      )
    `);
  }

  async addProduct(product: any) {
    const { name, ...properties } = product;
    if (!name) throw new BadRequestException('Name is required');

    const propsJson = JSON.stringify(properties);
    try {
      await this.db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsJson]);
    } catch (e) {
      throw new BadRequestException('Product already exists or invalid data');
    }
  }

  async downloadProduct(name: string) {
    const product = await this.db.get('SELECT properties FROM products WHERE name = ?', [name]);
    if (!product) {
      throw new BadRequestException('Product not found');
    }
    // The schema asks for the data as a string in the response object
    return { data: product.properties };
  }

  async uploadProduct(name: string, data: string) {
    // Validate that data is a valid JSON string (since it comes from /download)
    try {
      JSON.parse(data);
    } catch (e) {
      throw new BadRequestException('Invalid data format');
    }

    const result = await this.db.run('UPDATE products SET properties = ? WHERE name = ?', [data, name]);
    if (result.changes === 0) {
      // If product doesn't exist, the prompt says "fully replaces any previous data", 
      // implying we should ensure it exists or handle it as an upsert.
      await this.db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, data]);
    }
  }

  async searchProducts(query: string) {
    const products = await this.db.all('SELECT name, properties FROM products');
    const results = products.filter(p => {
      const props = JSON.parse(p.properties);
      const allValues = [p.name, ...Object.values(props)].map(v => String(v).toLowerCase());
      return allValues.some(v => v.includes(query.toLowerCase()));
    });

    return {
      results: results.map(p => ({
        name: p.name,
        ...JSON.parse(p.properties)
      }))
    };
  }
}