import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';
import * as path from 'path';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;

  onModuleInit() {
    this.db = new sqlite3.Database(path.join(process.cwd(), 'db.sqlite3'));
    this.initDb();
  }

  private initDb() {
    this.db.serialize(() => {
      this.db.run(`
        CREATE TABLE IF NOT EXISTS carts (
          cart_id TEXT PRIMARY KEY
        )
      `);
      this.db.run(`
        CREATE TABLE IF NOT EXISTS cart_items (
          cart_id TEXT,
          item_id INTEGER,
          count INTEGER,
          PRIMARY KEY (cart_id, item_id),
          FOREIGN KEY (cart_id) REFERENCES carts(cart_id)
        )
      `);
    });
  }

  async createCart(): Promise<{ cart_id: string }> {
    const cart_id = uuidv4();
    return new Promise((resolve, reject) => {
      this.db.run('INSERT INTO carts (cart_id) VALUES (?)', [cart_id], (err) => {
        if (err) reject(err);
        else resolve({ cart_id });
      });
    });
  }

  async addToCart(cart_id: string, item_id: number, count: number): Promise<void> {
    return new Promise((resolve, reject) => {
      // Check if cart exists
      this.db.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id], (err, row) => {
        if (err) return reject(err);
        if (!row) return reject(new NotFoundException('Cart not found'));

        // Update or Insert item count
        this.db.get('SELECT count FROM cart_items WHERE cart_id = ? AND item_id = ?', [cart_id, item_id], (err, row) => {
          if (err) return reject(err);
          
          const currentCount = row ? row.count : 0;
          const newCount = currentCount + count;

          if (newCount <= 0) {
            // Remove item if count drops to 0 or below
            this.db.run('DELETE FROM cart_items WHERE cart_id = ? AND item_id = ?', [cart_id, item_id], (err) => {
              if (err) reject(err);
              else resolve();
            });
          } else {
            this.db.run(
              'INSERT INTO cart_items (cart_id, item_id, count) VALUES (?, ?, ?) ON CONFLICT(cart_id, item_id) DO UPDATE SET count = ?',
              [cart_id, item_id, newCount, newCount],
              (err) => {
                if (err) reject(err);
                else resolve();
              }
            );
          }
        });
      });
    });
  }

  async retrieveCart(cart_id: string): Promise<{ items: { item_id: number, count: number }[] }> {
    return new Promise((resolve, reject) => {
      this.db.get('SELECT cart_id FROM carts WHERE cart_id = ?', [cart_id], (err, row) => {
        if (err) return reject(err);
        if (!row) return reject(new NotFoundException('Cart not found'));

        this.db.all('SELECT item_id, count FROM cart_items WHERE cart_id = ?', [cart_id], (err, rows) => {
          if (err) reject(err);
          else resolve({ items: rows });
        });
      });
    });
  }
}