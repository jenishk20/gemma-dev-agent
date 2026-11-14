import { Injectable, OnModuleInit, BadRequestException, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { open } from 'sqlite';
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
        timestamp TEXT NOT NULL
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
    const validDirections = ['<', '>', '<=', '>='];
    if (!validDirections.includes(direction)) {
      throw new BadRequestException('Invalid direction operator');
    }

    // Basic date validation
    if (isNaN(Date.parse(date))) {
      throw new BadRequestException('Invalid date format');
    }

    // Using a parameterized query for the date, but the operator must be hardcoded/whitelisted
    // because SQL parameters cannot be used for operators.
    const query = `SELECT id, timestamp FROM clicks WHERE timestamp ${direction} ?`;
    const rows = await this.db.all(query, [date]);

    if (!rows || rows.length === 0) {
      throw new NotFoundException('No clicks found');
    }

    return rows;
  }
}