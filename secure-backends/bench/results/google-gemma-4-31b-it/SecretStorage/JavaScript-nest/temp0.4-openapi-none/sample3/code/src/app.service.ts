import { Injectable, OnModuleInit, UnauthorizedException, BadRequestException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';
import { open } from 'sqlite';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;
  private readonly jwtSecret = process.env.APP_SECRET || 'default_secret_key';

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT UNIQUE,
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
      await this.db.run(
        'INSERT INTO users (email, username, password) VALUES (?, ?, ?)',
        [email, username, hashedPassword],
      );
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

    const token = jwt.sign({ username: user.username, email: user.email }, this.jwtSecret, { expiresIn: '1h' });
    return { token, message: 'Login successful' };
  }

  async setSecret(username: string, secret: string, token: string) {
    this.verifyToken(token);
    const payload = this.decodeToken(token);
    
    if (payload.username !== username) {
      throw new UnauthorizedException('Token does not match the provided username');
    }

    await this.db.run(
      'INSERT INTO secrets (username, secret_value) VALUES (?, ?) ON CONFLICT(username) DO UPDATE SET secret_value = excluded.secret_value',
      [username, secret],
    );
    return { message: 'Secret has been set successfully' };
  }

  async getSecret(username: string, token: string) {
    this.verifyToken(token);
    const payload = this.decodeToken(token);

    if (payload.username !== username) {
      throw new UnauthorizedException('Token does not match the provided username');
    }

    const row = await this.db.get('SELECT secret_value FROM secrets WHERE username = ?', [username]);
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

  private decodeToken(token: string) {
    return jwt.decode(token) as any;
  }
}