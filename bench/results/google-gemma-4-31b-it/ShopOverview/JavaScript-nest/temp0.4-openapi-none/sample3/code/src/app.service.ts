import { Injectable, OnModuleInit, UnauthorizedException, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;
  private readonly secret = process.env.APP_SECRET || 'default_secret_key';

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    const run = promisify(this.db.run.bind(this.db));

    await run(`CREATE TABLE IF NOT EXISTS merchants (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE,
      name TEXT,
      password TEXT
    )`);

    await run(`CREATE TABLE IF NOT EXISTS wares (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      merchant_id INTEGER,
      name TEXT,
      description TEXT,
      price REAL,
      FOREIGN KEY(merchant_id) REFERENCES merchants(id)
    )`);
  }

  private run(sql: string, params: any[] = []) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function (err) {
        if (err) reject(err);
        else resolve(this);
      });
    });
  }

  private all(sql: string, params: any[] = []) {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  private get(sql: string, params: any[] = []) {
    return new Promise((resolve, reject) => {
      this.db.get(sql, params, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  }

  async registerMerchant(email: string, name: string, password: string) {
    const hashedPassword = await bcrypt.hash(password, 10);
    try {
      await this.run('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', [email, name, hashedPassword]);
    } catch (e) {
      throw new BadRequestException('Merchant already exists');
    }
  }

  async loginMerchant(email: string, password: string) {
    const merchant = await this.get('SELECT * FROM merchants WHERE email = ?', [email]);
    if (!merchant || !(await bcrypt.compare(password, merchant.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }
    return jwt.sign({ id: merchant.id, email: merchant.email }, this.secret, { expiresIn: '1h' });
  }

  verifyToken(token: string) {
    try {
      return jwt.verify(token, this.secret) as any;
    } catch (e) {
      throw new UnauthorizedException();
    }
  }

  async uploadWares(merchantId: number, csv: string) {
    const lines = csv.split('\n').filter(line => line.trim() !== '');
    for (const line of lines) {
      const [name, description, priceStr] = line.split(',').map(s => s.trim());
      const price = parseFloat(priceStr);
      if (!name || isNaN(price)) {
        throw new BadRequestException('Invalid CSV format');
      }
      await this.run('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', [merchantId, name, description, price]);
    }
  }

  async getWares(minPrice?: number, maxPrice?: number) {
    let query = `
      SELECT w.name, w.price, w.description, m.email 
      FROM wares w 
      JOIN merchants m ON w.merchant_id = m.id 
      WHERE 1=1
    `;
    const params: any[] = [];

    if (minPrice !== undefined) {
      query += ' AND w.price >= ?';
      params.push(minPrice);
    }
    if (maxPrice !== undefined) {
      query += ' AND w.price <= ?';
      params.push(maxPrice);
    }

    return this.all(query, params);
  }
}