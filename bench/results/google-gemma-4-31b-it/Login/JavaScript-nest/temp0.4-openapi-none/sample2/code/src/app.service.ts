import { Injectable, OnModuleInit, BadRequestException, UnauthorizedException } from '@nestjs/common';
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
    await run(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        name TEXT
      )
    `);
  }

  private async get(sql: string, params: any[] = []): Promise<any[]> {
    const all = promisify(this.db.all.bind(this.db));
    return all(sql, params);
  }

  private async run(sql: string, params: any[] = []): Promise<void> {
    const run = promisify(this.db.run.bind(this.db));
    await run(sql, params);
  }

  async register(userData: any) {
    const { email, password, name } = userData;
    if (!email || !password || !name) {
      throw new BadRequestException('Missing required fields');
    }

    try {
      const hashedPassword = await bcrypt.hash(password, 10);
      await this.run(
        'INSERT INTO users (email, password, name) VALUES (?, ?, ?)',
        [email, hashedPassword, name]
      );
      return { message: 'Registration successful' };
    } catch (error) {
      if (error.message.includes('UNIQUE constraint failed')) {
        throw new BadRequestException('Email already in use');
      }
      throw error;
    }
  }

  async login(loginData: any) {
    const { email, password } = loginData;
    if (!email || !password) {
      throw new BadRequestException('Email and password are required');
    }

    const users = await this.get('SELECT * FROM users WHERE email = ?', [email]);
    const user = users[0];

    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const token = jwt.sign({ userId: user.id, email: user.email }, this.secret, {
      expiresIn: '24h',
    });

    return {
      token,
      message: 'Login successful',
    };
  }
}