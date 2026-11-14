import { Injectable, OnModuleInit, InternalServerErrorException } from '@nestjs/common';
import { open } from 'sqlite';
import * as sqlite3 from 'sqlite3';
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
      CREATE TABLE IF NOT EXISTS services (
        serviceId TEXT PRIMARY KEY,
        tokenHash TEXT NOT NULL,
        lastNotification DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  async registerHeartbeat(serviceId: string, token: string) {
    try {
      const tokenHash = await bcrypt.hash(token, 10);
      const service = await this.db.get('SELECT tokenHash FROM services WHERE serviceId = ?', [serviceId]);

      if (service) {
        const isMatch = await bcrypt.compare(token, service.tokenHash);
        if (!isMatch) {
          throw new InternalServerErrorException('Unauthorized token');
        }
        await this.db.run(
          'UPDATE services SET lastNotification = CURRENT_TIMESTAMP WHERE serviceId = ?',
          [serviceId],
        );
      } else {
        await this.db.run(
          'INSERT INTO services (serviceId, tokenHash, lastNotification) VALUES (?, ?, CURRENT_TIMESTAMP)',
          [serviceId, tokenHash],
        );
      }
    } catch (error) {
      if (error instanceof InternalServerErrorException) throw error;
      throw new InternalServerErrorException('Database error occurred');
    }
  }

  async getServicesByToken(token: string) {
    try {
      const allServices = await this.db.all('SELECT serviceId, tokenHash, lastNotification FROM services');
      const authorizedServices = [];

      for (const service of allServices) {
        const isMatch = await bcrypt.compare(token, service.tokenHash);
        if (isMatch) {
          authorizedServices.push({
            serviceId: service.serviceId,
            lastNotification: service.lastNotification,
          });
        }
      }

      return authorizedServices;
    } catch (error) {
      throw new InternalServerErrorException('Database error occurred');
    }
  }
}