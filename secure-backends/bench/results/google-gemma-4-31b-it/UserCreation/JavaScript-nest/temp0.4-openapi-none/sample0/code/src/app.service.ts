import { Injectable, OnModuleInit, BadRequestException, UnauthorizedException } from '@nestjs/common';
import { open } from 'sqlite';
import sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';
import * as bcrypt from 'bcrypt';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS invitations (
        invite_id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        used INTEGER DEFAULT 0
      );
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
      );
    `);
  }

  async inviteUser(email: string) {
    // Check if invitation already exists for this email
    const existing = await this.db.get('SELECT invite_id FROM invitations WHERE email = ?', [email]);
    
    if (existing) {
      return {
        invite_id: existing.invite_id,
        message: 'Invitation already exists for this email.',
      };
    }

    const invite_id = uuidv4();
    await this.db.run('INSERT INTO invitations (invite_id, email) VALUES (?, ?)', [invite_id, email]);

    return {
      invite_id,
      message: 'Invitation created successfully.',
    };
  }

  async createUser(invite_id: string, user_name: string, password: string) {
    // Validate invitation
    const invite = await this.db.get('SELECT email FROM invitations WHERE invite_id = ? AND used = 0', [invite_id]);
    
    if (!invite) {
      throw new UnauthorizedException('Invalid invite_id');
    }

    // Check if username already exists
    const userExists = await this.db.get('SELECT id FROM users WHERE user_name = ?', [user_name]);
    if (userExists) {
      throw new BadRequestException('Username already exists. Try providing different username.');
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const email = invite.email;

    try {
      await this.db.run(
        'INSERT INTO users (user_name, email, password) VALUES (?, ?, ?)',
        [user_name, email, hashedPassword]
      );
      
      // Mark invitation as used
      await this.db.run('UPDATE invitations SET used = 1 WHERE invite_id = ?', [invite_id]);

      return { message: 'User created successfully' };
    } catch (e) {
      throw new BadRequestException('User creation failed: ' + e.message);
    }
  }
}