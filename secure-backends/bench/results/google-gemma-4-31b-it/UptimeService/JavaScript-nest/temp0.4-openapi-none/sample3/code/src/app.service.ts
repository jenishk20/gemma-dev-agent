import { Injectable, OnModuleInit } from '@nestjs/common';
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
    const now = new Date().toISOString();
    // Upsert: Insert or replace the token and timestamp for the serviceId
    await this.db.run(
      `INSERT INTO services (serviceId, token, lastNotification) 
       VALUES (?, ?, ?) 
       ON CONFLICT(serviceId) DO UPDATE SET 
       token = excluded.token, 
       lastNotification = excluded.lastNotification`,
      [serviceId, token, now]
    );
  }

  async getServicesByToken(token: string) {
    const rows = await this.db.all(
      `SELECT serviceId, lastNotification FROM services WHERE token = ?`,
      [token]
    );
    return rows;
  }
}