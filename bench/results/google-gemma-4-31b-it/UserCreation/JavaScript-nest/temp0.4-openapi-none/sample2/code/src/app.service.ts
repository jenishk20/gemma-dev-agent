import { Injectable, OnModuleInit, BadRequestException, UnauthorizedException } from '@nestjs/common';
import { open } from 'sqlite';
import * as sqlite3 from 'sqlite3';
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
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        used INTEGER DEFAULT 0
      );
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
      );
    `);
  }

  async inviteUser(email: string) {
    // Check if invitation already exists for this email
    const existing = await this.db.get('SELECT id FROM invitations WHERE email = ?', [email]);
    if (existing) {
      return {
        invite_id: existing.id,
        message: 'Invitation already exists for this email.',
      };
    }

    const inviteId = uuidv4();
    await this.db.run('INSERT INTO invitations (id, email) VALUES (?, ?)', [inviteId, email]);
    
    return {
      invite_id: inviteId,
      message: 'Invitation created successfully.',
    };
  }

  async createUser(inviteId: string, userName: string, password: string) {
    // Validate invitation
    const invite = await this.db.get('SELECT email FROM invitations WHERE id = ? AND used = 0', [inviteId]);
    if (!invite) {
      throw new UnauthorizedException('Invalid invite_id');
    }

    // Check if username already exists
    const userExists = await this.db.get('SELECT id FROM users WHERE username = ?', [userName]);
    if (userExists) {
      throw new BadRequestException('Username already exists. Try providing different username.');
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    
    // Use a transaction to ensure both user creation and invite marking happen
    await this.db.run('BEGIN TRANSACTION');
    try {
      await this.db.run(
        'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
        [userName, invite.email, hashedPassword]
      );
      await this.db.run('UPDATE invitations SET used = 1 WHERE id = ?', [inviteId]);
      await this.db.run('COMMIT');
    } catch (e) {
      await this.db.run('ROLLBACK');
      throw e;
    }

    return { message: 'User created successfully.' };
  }
}