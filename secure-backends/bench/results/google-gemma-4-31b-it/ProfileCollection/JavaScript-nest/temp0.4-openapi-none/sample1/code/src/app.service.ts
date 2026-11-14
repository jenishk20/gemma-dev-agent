import { Injectable, OnModuleInit, ForbiddenException, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { open } from 'sqlite';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.DatabaseDriver,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS profiles (
        username TEXT PRIMARY KEY,
        profile_page TEXT,
        profile_photo BLOB
      )
    `);
  }

  async createProfile(username: string, profilePage: string, profilePhoto: Buffer) {
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