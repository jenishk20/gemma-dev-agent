import { Injectable, OnModuleInit, UnauthorizedException, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';
import { open } from 'sqlite';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;
  private secret = process.env.APP_SECRET || 'default_secret_key';

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS merchants (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        name TEXT,
        password TEXT
      );
      CREATE TABLE IF NOT EXISTS wares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchantId TEXT,
        name TEXT,
        description TEXT,
        price REAL,
        FOREIGN KEY(merchantId) REFERENCES merchants(id)
      );
    `);
  }

  async registerMerchant(email, name, password) {
    const hashed = await bcrypt.hash(password, 10);
    const id = require('uuid').v4();
    try {
      await this.db.run('INSERT INTO merchants (id, email, name, password) VALUES (?, ?, ?, ?)', [id, email, name, hashed]);
      return { id };
    } catch (e) {
      throw new BadRequestException('Email already exists');
    }
  }

  async loginMerchant(email, password) {
    const user = await this.db.get('SELECT * FROM merchants WHERE email = ?', [email]);
    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }
    const token = jwt.sign({ id: user.id, email: user.email }, this.secret, { expiresIn: '1h' });
    return token;
  }

  async uploadWares(token, csvString) {
    const payload = this.verifyToken(token);
    const lines = csvString.split('\n').filter(line => line.trim() !== '');
    
    // Basic CSV parsing: name, description, price
    for (const line of lines) {
      const [name, description, priceStr] = line.split(',').map(s => s.trim());
      const price = parseFloat(priceStr);
      if (!name || isNaN(price)) {
        throw new BadRequestException('Invalid CSV format');
      }
      await this.db.run('INSERT INTO wares (merchantId, name, description, price) VALUES (?, ?, ?, ?)', 
        [payload.id, name, description, price]);
    }
  }

  async getWaresHtml(minPrice, maxPrice) {
    let query = `
      SELECT w.name, w.description, w.price, m.email 
      FROM wares w 
      JOIN merchants m ON w.merchantId = m.id 
      WHERE 1=1
    `;
    const params = [];

    if (minPrice) {
      query += ' AND w.price >= ?';
      params.push(minPrice);
    }
    if (maxPrice) {
      query += ' AND w.price <= ?';
      params.push(maxPrice);
    }

    const rows = await this.db.all(query, params);
    
    let html = '<table><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>';
    rows.forEach(row => {
      html += `<tr><td>${row.name}</td><td>${row.price}</td><td>${row.description}</td><td>${row.email}</td></tr>`;
    });
    html += '</tbody></table>';
    return html;
  }

  verifyToken(token: string) {
    try {
      return jwt.verify(token, this.secret);
    } catch (e) {
      throw new UnauthorizedException('Invalid or expired session');
    }
  }
}