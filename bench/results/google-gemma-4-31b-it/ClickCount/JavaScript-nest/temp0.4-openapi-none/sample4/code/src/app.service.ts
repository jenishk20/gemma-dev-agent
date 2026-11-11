import { Injectable, OnModuleInit, BadRequestException, NotFoundException } from '@nestjs/common';
import { open, Database } from 'sqlite';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService implements OnModuleInit {
  private db: Database;

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
    const allowedDirections = ['<', '>', '<=', '>='];
    if (!allowedDirections.includes(direction)) {
      throw new BadRequestException('Invalid direction. Allowed values: <, >, <=, >=');
    }

    // Basic date format validation (YYYY-MM-DD)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      throw new BadRequestException('Invalid date format. Expected YYYY-MM-DD');
    }

    // SQLite allows comparing ISO strings. 
    // We append T00:00:00Z to the date to ensure correct comparison with timestamps.
    const formattedDate = `${date}T00:00:00Z`;
    
    // Note: Using template literal for the operator because operators cannot be parameterized in SQL
    const query = `SELECT id, timestamp FROM clicks WHERE timestamp ${direction} ?`;
    const rows = await this.db.all(query, [formattedDate]);

    if (rows.length === 0) {
      throw new NotFoundException('No clicks found');
    }

    return rows;
  }
}