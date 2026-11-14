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
        properties TEXT
      )
    `);
  }

  async addProduct(product: any) {
    const { name, ...properties } = product;
    if (!name) throw new BadRequestException('Product name is required');

    const propsJson = JSON.stringify(properties);
    try {
      await this.db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, propsJson]);
    } catch (e) {
      throw new BadRequestException('Product already exists');
    }
  }

  async downloadProduct(name: string) {
    const row = await this.db.get('SELECT properties FROM products WHERE name = ?', [name]);
    if (!row) throw new BadRequestException('Product not found');
    
    return { data: row.properties };
  }

  async uploadProduct(name: string, data: string) {
    // Validate that data is a valid JSON string representing properties
    try {
      JSON.parse(data);
    } catch (e) {
      throw new BadRequestException('Invalid data format');
    }

    const result = await this.db.run('UPDATE products SET properties = ? WHERE name = ?', [data, name]);
    if (result.changes === 0) {
      // If product doesn't exist, we create it (as per "fully replaces any previous data")
      await this.db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, data]);
    }
  }

  async searchProducts(query: string) {
    const products = await this.db.all('SELECT * FROM products');
    const results = [];

    for (const product of products) {
      const props = JSON.parse(product.properties);
      const fullProduct = { name: product.name, ...props };
      
      // Search in name or any value of the properties
      const matchName = product.name.toLowerCase().includes(query.toLowerCase());
      const matchProps = Object.values(props).some(val => 
        String(val).toLowerCase().includes(query.toLowerCase())
      );

      if (matchName || matchProps) {
        results.push(fullProduct);
      }
    }

    return { results };
  }
}