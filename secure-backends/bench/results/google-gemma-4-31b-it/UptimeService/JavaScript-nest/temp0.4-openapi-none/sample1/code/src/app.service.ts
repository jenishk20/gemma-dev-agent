import { Injectable, OnModuleInit, InternalServerErrorException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { open } from 'sqlite';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS services (
        serviceId TEXT PRIMARY KEY,
        token TEXT NOT NULL,
        lastNotification DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  async registerHeartbeat(serviceId: string, token: string) {
    try {
      const now = new Date().toISOString();
      // Upsert: Insert new service or update existing one if serviceId exists
      await this.db.run(
        `INSERT INTO services (serviceId, token, lastNotification) 
         VALUES (?, ?, ?) 
         ON CONFLICT(serviceId) DO UPDATE SET 
         token = excluded.token, 
         lastNotification = excluded.lastNotification`,
        [serviceId, token, now]
      );
    } catch (error) {
      throw new InternalServerErrorException('Database error occurred');
    }
  }

  async getServicesByToken(token: string) {
    try {
      const rows = await this.db.all(
        'SELECT serviceId, lastNotification FROM services WHERE token = ?',
        [token]
      );
      return rows;
    } catch (error) {
      throw new InternalServerErrorException('Database error occurred');
    }
  }
}