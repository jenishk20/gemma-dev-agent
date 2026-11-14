import { Injectable, OnModuleInit, NotFoundException, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';
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
    const cart_id = uuidv4();
    await this.run('INSERT INTO carts (cart_id) VALUES (?)', [cart_id]);
    return { cart_id };
  }

  async addToCart(cart_id: string, item_id: number, count: number) {
    const cart = await this.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id]);
    if (!cart) {
      throw new NotFoundException('Cart not found');
    }

    if (typeof item_id !== 'number' || typeof count !== 'number') {
      throw new BadRequestException('Invalid item_id or count');
    }

    // Get current count
    const current = await this.get('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', [cart_id, item_id]);
    const newCount = (current ? current.count : 0) + count;

    if (newCount < 0) {
      throw new BadRequestException('Item count cannot be negative');
    }

    if (newCount === 0) {
      await this.run('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', [cart_id, item_id]);
    } else {
      await this.run(
        'INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?) ON CONFLICT(cart_id, item_id) DO UPDATE SET count = excluded.count',
        [cart_id, item_id, newCount]
      );
    }

    return { success: true };
  }

  async retrieveCart(cart_id: string) {
    const cart = await this.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id]);
    if (!cart) {
      throw new NotFoundException('Cart not found');
    }

    const items = await this.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cart_id]);
    return { items };
  }
}