import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    
    const run = promisify(this.db.run.bind(this.db));
    
    // Initialize tables
    await run(`
      CREATE TABLE IF NOT EXISTS carts (
        cart_id TEXT PRIMARY KEY
      )
    `);
    
    await run(`
      CREATE TABLE IF NOT EXISTS cart_items (
        cart_id TEXT,
        item_id INTEGER,
        count INTEGER,
        PRIMARY KEY (cart_id, item_id),
        FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
      )
    `);
  }

  private async run(sql: string, params: any[] = []): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  private async all(sql: string, params: any[] = []): Promise<any[]> {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  async createCart() {
    const cartId = uuidv4();
    await this.run('INSERT INTO carts (cart_id) VALUES (?)', [cartId]);
    return { cart_id: cartId };
  }

  async addToCart(cartId: string, itemId: number, count: number) {
    // Check if cart exists
    const carts = await this.all('SELECT cart_id FROM carts WHERE cart_id = ?', [cartId]);
    if (carts.length === 0) {
      throw new NotFoundException('Cart not found');
    }

    // Upsert item count
    await this.run(
      `INSERT INTO cart_items (cart_id, item_id, count) 
       VALUES (?, ?, ?) 
       ON CONFLICT(cart_id, item_id) 
       DO UPDATE SET count = count + excluded.count`,
      [cartId, itemId, count]
    );

    // Remove items with count <= 0
    await this.run('DELETE FROM cart_items WHERE cart_id = ? AND count <= 0', [cartId]);
  }

  async retrieveCart(cartId: string) {
    const carts = await this.all('SELECT cart_id FROM carts WHERE cart_id = ?', [cartId]);
    if (carts.length === 0) {
      throw new NotFoundException('Cart not found');
    }

    const items = await this.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cartId]);
    return { items };
  }
}