import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;
  private run = null;
  private get = null;
  private all = null;

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    
    // Promisify sqlite methods for async/await usage
    this.run = promisify(this.db.run).bind(this.db);
    this.get = promisify(this.db.get).bind(this.db);
    this.all = promisify(this.db.all).bind(this.db);

    await this.run(`
      CREATE TABLE IF NOT EXISTS carts (
        cart_id TEXT PRIMARY KEY
      )
    `);
    await this.run(`
      CREATE TABLE IF NOT EXISTS cart_items (
        cart_id TEXT,
        item_id INTEGER,
        count INTEGER,
        PRIMARY KEY (cart_id, item_id),
        FOREIGN KEY (cart_id REFERENCES carts(cart_id))
      )
    `);
  }

  async createCart() {
    const cartId = uuidv4();
    await this.run('INSERT INTO carts (cart_id) VALUES (?)', [cartId]);
    return { cart_id: cartId };
  }

  async addToCart(cartId: string, itemId: number, count: number) {
    const cart = await this.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cartId]);
    if (!cart) {
      throw new NotFoundException('Cart not found');
    }

    // Use UPSERT logic: add count to existing or insert new
    await this.run(`
      INSERT INTO cart_items (cart_id, item_id, count) 
      VALUES (?, ?, ?) 
      ON CONFLICT(cart_id, item_id) DO UPDATE SET count = count + excluded.count
    `, [cartId, itemId, count]);

    // Remove items if count drops to 0 or below
    await this.run('DELETE FROM cart_items WHERE count <= 0');
  }

  async retrieveCart(cartId: string) {
    const cart = await this.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cartId]);
    if (!cart) {
      throw new NotFoundException('Cart not found');
    }

    const items = await this.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cartId]);
    return { items };
  }
}