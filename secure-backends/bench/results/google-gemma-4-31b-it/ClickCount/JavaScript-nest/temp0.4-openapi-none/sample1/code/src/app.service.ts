import { Injectable, OnModuleInit, BadRequestException, NotFoundException } from '@nestjs/common';
import { open } from 'sqlite';
import sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS clicks (
        id TEXT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  async registerClick() {
    const id = uuidv4();
    const timestamp = new Date().toISOString();
    await this.db.run('INSERT INTO clicks (id, timestamp) VALUES (?, ?)', [id, timestamp]);
    return { id, timestamp };
  }

  async getClicks(date: string, direction: string) {
    // Validate date format (YYYY-MM-DD)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      throw new BadRequestException('Invalid date format. Expected YYYY-MM-DD');
    }

    // Validate direction operator
    const validOperators = ['<', '>', '<=', '>='];
    if (!validOperators.includes(direction)) {
      throw new BadRequestException('Invalid direction operator');
    }

    // SQLite handles ISO strings for comparison. 
    // We append ' 00:00:00' to the date to ensure proper comparison with timestamps.
    const query = `SELECT id, timestamp FROM clicks WHERE timestamp ${direction} ?`;
    const rows = await this.db.all(query, [`${date} 00:00:00`]);

    if (!rows || rows.length === 0) {
      throw new NotFoundException('No clicks found');
    }

    return rows;
  }
}