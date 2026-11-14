import { Injectable, OnModuleInit, BadRequestException, UnauthorizedException } from '@nestjs/common';
import { open } from 'sqlite';
import * as sqlite3 from 'sqlite3';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;
  private readonly secret = process.env.APP_SECRET || 'default-secret-key';

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL
      )
    `);
  }

  async register(userData: { email: string; password: string; name: string }) {
    const { email, password, name } = userData;

    try {
      const hashedPassword = await bcrypt.hash(password, 10);
      await this.db.run(
        'INSERT INTO users (email, password, name) VALUES (?, ?, ?)',
        [email, hashedPassword, name]
      );
      return { message: 'Registration successful' };
    } catch (error) {
      if (error.message.includes('UNIQUE constraint failed')) {
        throw new BadRequestException('Email already in use or invalid data');
      }
      throw error;
    }
  }

  async login(credentials: { email: string; password: string }) {
    const { email, password } = credentials;

    const user = await this.db.get('SELECT * FROM users WHERE email = ?', [email]);

    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const token = jwt.sign({ userId: user.id, email: user.email }, this.secret, {
      expiresIn: '1h',
    });

    return {
      token,
      message: 'Login successful',
    };
  }
}