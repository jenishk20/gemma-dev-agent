import { Injectable, OnModuleInit } from '@nestjs/common';
import { open } from 'sqlite';
import { openWithDb } from 'sqlite3';
import * as sqlite3 from 'sqlite3';

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
        lastNotification TEXT NOT NULL
      )
    `);
  }

  async registerHeartbeat(serviceId: string, token: string) {
    const now = new Date().toISOString();
    // Upsert: Insert or replace the record if serviceId exists
    await this.db.run(
      'INSERT INTO services (serviceId, token, lastNotification) VALUES (?, ?, ?) ON CONFLICT(serviceId) DO UPDATE SET token = excluded.token, lastNotification = excluded.lastNotification',
      [serviceId, token, now]
    );
    return { success: true };
  }

  async getServicesByToken(token: string) {
    const rows = await this.db.all(
      'SELECT serviceId, lastNotification FROM services WHERE token = ?',
      [token]
    );
    return rows;
  }
}