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

  private async query(sql: string, params: any[] = []) {
    return new Promise<any[]>((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  private async run(sql: string, params: any[] = []) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function(err) {
        if (err) reject(err);
        else resolve(this);
      });
    });
  }

  async registerMerchant(email: string, name: string, password: string) {
    const hashed = await bcrypt.hash(password, 10);
    try {
      await this.run('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', [email, name, hashed]);
      return { success: true };
    } catch (e) {
      throw new BadRequestException('Merchant already exists or invalid input');
    }
  }

  async loginMerchant(email: string, password: string) {
    const rows = await this.query('SELECT * FROM merchants WHERE email = ?', [email]);
    if (rows.length === 0) throw new UnauthorizedException('Invalid email or password');
    
    const merchant = rows[0];
    const match = await bcrypt.compare(password, merchant.password);
    if (!match) throw new UnauthorizedException('Invalid email or password');

    const token = jwt.sign({ id: merchant.id, email: merchant.email }, this.secret, { expiresIn: '1h' });
    return token;
  }

  async uploadWares(merchantId: number, csvString: string) {
    const lines = csvString.split('\n').filter(line => line.trim() !== '');
    for (const line of lines) {
      const [name, description, priceStr] = line.split(',').map(s => s.trim());
      const price = parseFloat(priceStr);
      if (!name || isNaN(price)) {
        throw new BadRequestException('Invalid CSV format: name, description, price required');
      }
      await this.run('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', [merchantId, name, description, price]);
    }
  }

  async getWares(minPrice?: number, maxPrice?: number) {
    let sql = `
      SELECT w.name, w.price, w.description, m.email 
      FROM wares w 
      JOIN merchants m ON w.merchant_id = m.id 
      WHERE 1=1
    `;
    const params: any[] = [];

    if (minPrice !== undefined) {
      sql += ' AND w.price >= ?';
      params.push(minPrice);
    }
    if (maxPrice !== undefined) {
      sql += ' AND w.price <= ?';
      params.push(maxPrice);
    }

    return await this.query(sql, params);
  }

  verifyToken(token: string) {
    try {
      return jwt.verify(token, this.secret) as any;
    } catch (e) {
      return null;
    }
  }
}