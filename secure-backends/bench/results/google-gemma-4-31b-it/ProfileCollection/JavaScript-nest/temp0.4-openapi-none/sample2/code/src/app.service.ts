import { Injectable, OnModuleInit, ForbiddenException, NotFoundException, BadRequestException } from '@nestjs/common';
import { open, Database } from 'sqlite';
import sqlite3 from 'sqlite3';

@Injectable()
export class AppService implements OnModuleInit {
  private db: Database;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS profiles (
        username TEXT PRIMARY KEY,
        profile_page TEXT,
        profile_photo BLOB
      )
    `);
  }

  async addProfile(username: string, profilePage: string, profilePhoto: Buffer) {
    if (!username || !profilePage || !profilePhoto) {
      throw new BadRequestException('Missing required fields');
    }

    try {
      await this.db.run(
        'INSERT INTO profiles (username, profile_page, profile_photo) VALUES (?, ?, ?)',
        [username, profilePage, profilePhoto]
      );
    } catch (e) {
      if (e.message.includes('UNIQUE constraint failed')) {
        throw new ForbiddenException('Profile already exists');
      }
      throw e;
    }
  }

  async getProfilePage(username: string): Promise<string> {
    const profile = await this.db.get('SELECT profile_page FROM profiles WHERE username = ?', [username]);
    if (!profile) {
      throw new NotFoundException('Profile not found');
    }
    return profile.profile_page;
  }

  async getProfilePhoto(username: string): Promise<Buffer> {
    const profile = await this.db.get('SELECT profile_photo FROM profiles WHERE username = ?', [username]);
    if (!profile) {
      throw new NotFoundException('Profile photo not found');
    }
    return profile.profile_photo;
  }
}