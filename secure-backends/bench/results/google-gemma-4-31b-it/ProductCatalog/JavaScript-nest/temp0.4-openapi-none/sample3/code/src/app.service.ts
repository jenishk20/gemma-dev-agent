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
      throw new BadRequestException('Product already exists or invalid data');
    }
  }

  async downloadProduct(name: string) {
    const product = await this.db.get('SELECT properties FROM products WHERE name = ?', [name]);
    if (!product) throw new BadRequestException('Product not found');
    
    return { data: product.properties };
  }

  async uploadProduct(name: string, data: string) {
    try {
      // Validate that data is a valid JSON string as it represents the properties
      JSON.parse(data);
      await this.db.run('UPDATE products SET properties = ? WHERE name = ?', [data, name]);
      
      const result = await this.db.get('SELECT 1 FROM products WHERE name = ?', [name]);
      if (!result) {
        // If product didn't exist, we create it (as per "fully replaces any previous data")
        await this.db.run('INSERT INTO products (name, properties) VALUES (?, ?)', [name, data]);
      }
    } catch (e) {
      throw new BadRequestException('Invalid upload data format');
    }
  }

  async searchProducts(query: string) {
    const products = await this.db.all('SELECT * FROM products');
    const results = products.filter(p => {
      const props = JSON.parse(p.properties || '{}');
      const allValues = [p.name, ...Object.values(props)].map(v => String(v).toLowerCase());
      return allValues.some(v => v.includes(query.toLowerCase()));
    }).map(p => {
      return {
        name: p.name,
        ...JSON.parse(p.properties || '{}')
      };
    });

    return { results };
  }
}