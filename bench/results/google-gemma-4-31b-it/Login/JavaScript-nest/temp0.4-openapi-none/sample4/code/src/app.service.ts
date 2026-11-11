import { Injectable, OnModuleInit, UnauthorizedException, BadRequestException } from '@nestjs/common';
import { open, Database } from 'sqlite';
import * as bcrypt from 'bcrypt';
import * as jwt from 'jsonwebtoken';

@Injectable()
export class AppService implements OnModuleInit {
  private db: Database;
  private readonly secret = process.env.APP_SECRET || 'default_secret_key';

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: 'sqlite',
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

    const existingUser = await this.db.get('SELECT id FROM users WHERE email = ?', [email]);
    if (existingUser) {
      throw new BadRequestException('Email already in use');
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    await this.db.run(
      'INSERT INTO users (email, password, name) VALUES (?, ?, ?)',
      [email, hashedPassword, name],
    );

    return { message: 'Registration successful' };
  }

  async login(credentials: { email: string; password: string }) {
    const { email, password } = credentials;

    const user = await this.db.get('SELECT * FROM users WHERE email = ?', [email]);
    if (!user) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const isPasswordValid = await bcrypt.compare(password, user.password);
    if (!isPasswordValid) {
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