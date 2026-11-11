import { Injectable, OnModuleInit, UnauthorizedException, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';
import { open } from 'sqlite';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;
  private readonly secretKey = process.env.APP_SECRET || 'default_secret_key';

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        username TEXT UNIQUE,
        password TEXT
      );
      CREATE TABLE IF NOT EXISTS secrets (
        username TEXT PRIMARY KEY,
        secret_value TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
      );
    `);
  }

  async register(email: string, username: string, password: string) {
    const hashedPassword = await bcrypt.hash(password, 10);
    try {
      await this.db.run('INSERT INTO users (email, username, password) VALUES (?, ?, ?)', [email, username, hashedPassword]);
      return { message: 'Registration successful' };
    } catch (e) {
      throw new BadRequestException('Email already in use or invalid data');
    }
  }

  async login(email: string, password: string) {
    const user = await this.db.get('SELECT * FROM users WHERE email = ?', [email]);
    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const token = jwt.sign({ username: user.username, email: user.email }, this.secretKey, { expiresIn: '1h' });
    return { token, message: 'Login successful' };
  }

  async setSecret(username: string, secret: string) {
    await this.db.run('INSERT OR REPLACE INTO secrets (username, secret_value) VALUES (?, ?)', [username, secret]);
    return { message: 'Secret has been set successfully' };
  }

  async getSecret(username: string) {
    const row = await this.db.get('SELECT secret_value FROM secrets WHERE username = ?', [username]);
    if (!row) {
      throw new BadRequestException('No secret found for this user');
    }
    return { secret: row.secret_value };
  }

  verifyToken(token: string) {
    try {
      return jwt.verify(token, this.secretKey);
    } catch (e) {
      throw new UnauthorizedException('Invalid authentication token');
    }
  }
}