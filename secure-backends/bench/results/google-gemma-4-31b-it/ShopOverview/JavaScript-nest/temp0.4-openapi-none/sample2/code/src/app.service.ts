import { Injectable, OnModuleInit, UnauthorizedException, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import * as jwt from 'jsonwebtoken';
import * as bcrypt from 'bcrypt';
import { open } from 'sqlite';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;
  private readonly secret = process.env.APP_SECRET || 'default_secret_key';

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS merchants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        name TEXT,
        password TEXT
      );
      CREATE TABLE IF NOT EXISTS wares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_id INTEGER,
        name TEXT,
        description TEXT,
        price REAL,
        FOREIGN KEY(merchant_id) REFERENCES merchants(id)
      );
    `);
  }

  async register(email: string, name: string, password: string) {
    const hashedPassword = await bcrypt.hash(password, 10);
    try {
      await this.db.run('INSERT INTO merchants (email, name, password) VALUES (?, ?, ?)', [email, name, hashedPassword]);
      return { success: true };
    } catch (e) {
      throw new BadRequestException('Merchant already exists or invalid input');
    }
  }

  async login(email: string, password: string) {
    const user = await this.db.get('SELECT * FROM merchants WHERE email = ?', [email]);
    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }
    const token = jwt.sign({ id: user.id, email: user.email }, this.secret, { expiresIn: '1h' });
    return token;
  }

  async uploadWares(token: string, csvContent: string) {
    const payload = this.verifyToken(token);
    const lines = csvContent.split('\n').filter(line => line.trim() !== '');
    
    // Expected columns: name, description, price
    for (const line of lines) {
      const [name, description, priceStr] = line.split(',').map(s => s.trim());
      const price = parseFloat(priceStr);
      if (!name || isNaN(price)) {
        throw new BadRequestException('Invalid CSV format: name, description, price required');
      }
      await this.db.run('INSERT INTO wares (merchant_id, name, description, price) VALUES (?, ?, ?, ?)', 
        [payload.id, name, description, price]);
    }
  }

  async getWaresHtml(minPrice: number, maxPrice: number) {
    let query = `
      SELECT w.name, w.price, w.description, m.email 
      FROM wares w 
      JOIN merchants m ON w.merchant_id = m.id 
      WHERE 1=1
    `;
    const params = [];

    if (minPrice !== undefined) {
      query += ' AND w.price >= ?';
      params.push(minPrice);
    }
    if (maxPrice !== undefined) {
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
      throw new UnauthorizedException('Unauthorized');
    }
  }
}