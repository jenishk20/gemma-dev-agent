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
    
    // Initialize Users table
    await run(`
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL
      )
    `);
  }

  private getDbGet() {
    return promisify(this.db.get.bind(this.db));
  }

  private getDbRun() {
    return promisify(this.db.run.bind(this.db));
  }

  async register(email: string, password: string, name: string) {
    const hashedPassword = await bcrypt.hash(password, 10);
    try {
      await this.getDbRun('INSERT INTO users (email, password, name) VALUES (?, ?, ?)', [email, hashedPassword, name]);
      return { message: 'Registration successful' };
    } catch (error) {
      if (error.message.includes('UNIQUE constraint failed')) {
        throw new BadRequestException('Email already in use');
      }
      throw new BadRequestException('Invalid data');
    }
  }

  async login(email: string, password: string) {
    const user = await this.getDbGet('SELECT * FROM users WHERE email = ?', [email]);
    
    if (!user || !(await bcrypt.compare(password, user.password))) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const token = jwt.sign(
      { userId: user.id, email: user.email },
      this.secret,
      { expiresIn: '1h' }
    );

    return {
      token,
      message: 'Login successful'
    };
  }
}