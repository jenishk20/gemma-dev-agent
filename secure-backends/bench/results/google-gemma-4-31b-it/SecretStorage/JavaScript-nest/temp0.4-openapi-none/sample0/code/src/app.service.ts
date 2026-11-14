import { Injectable, OnModuleInit, UnauthorizedException, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;
  private jwtSecret: string;

  async onModuleInit() {
    this.jwtSecret = process.env.APP_SECRET || 'default_secret_key';
    this.db = new sqlite3.Database('db.sqlite3');
    
    const run = promisify(this.db.run.bind(this.db));
    
    // Initialize Tables
    await run(`CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE,
      username TEXT UNIQUE,
      password TEXT
    )`);
    
    await run(`CREATE TABLE IF NOT EXISTS secrets (
      username TEXT PRIMARY KEY,
      secret_value TEXT,
      FOREIGN KEY(username) REFERENCES users(username)
    )`);
  }

  private async queryOne<T>(sql: string, params: any[]): Promise<T | null> {
    const get = promisify(this.db.get.bind(this.db));
    return await get(sql, params) as T | null;
  }

  private async runQuery(sql: string, params: any[]): Promise<void> {
    const run = promisify(this.db.run.bind(this.db));
    await run(sql, params);
  }

  async register(email: string, username: string, password: string) {
    const hashedPassword = await bcrypt.hash(password, 10);
    try {
      await this.runQuery(
        'INSERT INTO users (email, username, password) VALUES (?, ?, ?)',
        [email, username, hashedPassword]
      );
      return { message: 'Registration successful' };
    } catch (e) {
      throw new BadRequestException('Email already in use or invalid data');
    }
  }

  async login(email: string, password: string) {
    const user = await this.queryOne<{ password: string }>('SELECT password FROM users WHERE email = ?', [email]);
    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }
    
    const token = jwt.sign({ email }, this.jwtSecret, { expiresIn: '1h' });
    return { token, message: 'Login successful' };
  }

  verifyToken(token: string): any {
    try {
      return jwt.verify(token, this.jwtSecret);
    } catch (e) {
      throw new UnauthorizedException('Invalid authentication token');
    }
  }

  async setSecret(username: string, secret: string, token: string) {
    this.verifyToken(token);
    
    // Verify that the user exists and the token belongs to a valid user
    const user = await this.queryOne<{ id: number }>('SELECT id FROM users WHERE username = ?', [username]);
    if (!user) throw new BadRequestException('User not found');

    await this.runQuery(
      'INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)',
      [username, secret]
    );
    return { message: 'Secret has been set successfully' };
  }

  async getSecret(username: string, token: string) {
    this.verifyToken(token);
    
    const row = await this.queryOne<{ secret_value: string }>('SELECT secret_value FROM secrets WHERE username = ?', [username]);
    if (!row) throw new BadRequestException('Secret not found for this user');
    
    return { secret: row.secret_value };
  }
}