import { Injectable, OnModuleInit, UnauthorizedException, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;
  private readonly jwtSecret = process.env.APP_SECRET || 'default-secret-key';

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    
    const run = promisify(this.db.run.bind(this.db));
    
    // Initialize Tables
    await run(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
        password TEXT
      )
    `);
    
    await run(`
      CREATE TABLE IF NOT EXISTS secrets (
        username TEXT PRIMARY KEY,
        secret_value TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
      )
    `);
  }

  private async get(sql: string, params: any[] = []): Promise<any> {
    return new Promise((resolve, reject) => {
      this.db.get(sql, params, (err, row) => {
        if (err) reject(err);
        else resolve(row);
      });
    });
  }

  private async run(sql: string, params: any[] = []): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  async register(email: string, username: string, password: string) {
    const existingUser = await this.get('SELECT id FROM users WHERE email = ? OR username = ?', [email, username]);
    if (existingUser) {
      throw new BadRequestException('Email or username already in use');
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    await this.run('INSERT INTO users (email, username, password) VALUES (?, ?, ?)', [email, username, hashedPassword]);
    return { message: 'Registration successful' };
  }

  async login(email: string, password: string) {
    const user = await this.get('SELECT * FROM users WHERE email = ?', [email]);
    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const token = jwt.sign({ username: user.username }, this.jwtSecret, { expiresIn: '1h' });
    return { token, message: 'Login successful' };
  }

  async setSecret(username: string, secret: string, token: string) {
    this.verifyToken(token);
    
    // Ensure the token belongs to the username they are trying to set a secret for
    const decoded = jwt.verify(token, this.jwtSecret) as any;
    if (decoded.username !== username) {
      throw new UnauthorizedException('Token does not match username');
    }

    await this.run(
      'INSERT INTO secrets (username, secret_value) VALUES (?, ?) ON CONFLICT(username) DO UPDATE SET secret_value = excluded.secret_value',
      [username, secret]
    );
    return { message: 'Secret has been set successfully' };
  }

  async getSecret(username: string, token: string) {
    this.verifyToken(token);
    
    const decoded = jwt.verify(token, this.jwtSecret) as any;
    if (decoded.username !== username) {
      throw new UnauthorizedException('Token does not match username');
    }

    const row = await this.get('SELECT secret_value FROM secrets WHERE username = ?', [username]);
    if (!row) {
      throw new BadRequestException('No secret found for this user');
    }
    return { secret: row.secret_value };
  }

  private verifyToken(token: string) {
    try {
      jwt.verify(token, this.jwtSecret);
    } catch (e) {
      throw new UnauthorizedException('Invalid authentication token');
    }
  }
}