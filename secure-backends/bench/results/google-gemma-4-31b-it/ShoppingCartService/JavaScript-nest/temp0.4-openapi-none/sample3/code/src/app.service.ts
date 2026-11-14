import { Injectable, OnModuleInit, NotFoundException, BadRequestException } from '@nestjs/common';
import { open } from 'sqlite';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS carts (
        cart_id TEXT PRIMARY KEY
      );
      CREATE TABLE IF NOT EXISTS cart_items (
        cart_id TEXT,
        item_id INTEGER,
        count INTEGER,
        PRIMARY KEY (cart_id, item_id),
        FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
      );
    `);
  }

  async createCart() {
    const cartId = uuidv4();
    await this.db.run('INSERT INTO carts (cart_id) VALUES (?)', [cartId]);
    return { cart_id: cartId };
  }

  async addToCart(cartId: string, itemId: number, count: number) {
    const cart = await this.db.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cartId]);
    if (!cart) {
      throw new NotFoundException('Cart not found');
    }

    const item = await this.db.get('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', [cartId, itemId]);
    
    if (item) {
      const newCount = item.count + count;
      if (newCount <= 0) {
        await this.db.run('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', [cartId, itemId]);
      } else {
        await this.db.run('UPDATE cart_items SET count = ? WHERE cart_id = ? AND item_id = ?', [newCount, cartId, itemId]);
      }
    } else {
      if (count <= 0) {
        throw new BadRequestException('Initial count must be positive');
      }
      await this.db.run('INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?)', [cartId, itemId, count]);
    }
    return { success: true };
  }

  async retrieveCart(cartId: string) {
    const cart = await this.db.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cartId]);
    if (!cart) {
      throw new NotFoundException('Cart not found');
    }

    const items = await this.db.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cartId]);
    return { items };
  }
}