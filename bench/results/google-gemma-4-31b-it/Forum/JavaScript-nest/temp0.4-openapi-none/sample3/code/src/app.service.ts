import { Injectable, OnModuleInit } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    
    const run = promisify(this.db.run.bind(this.db));
    await run(`
      CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  async createMessage(username: string, content: string) {
    const run = promisify(this.db.run.bind(this.db));
    await run(
      'INSERT INTO messages (username, content) VALUES (?, ?)',
      [username, content]
    );
  }

  async getMessages(limit: number, offset: number, sort: 'ASC' | 'DESC') {
    const all = promisify(this.db.all.bind(this.db));
    const query = `
      SELECT username, content, created_at 
      FROM messages 
      ORDER BY created_at ${sort} 
      LIMIT ? OFFSET ?
    `;
    return await all(query, [limit, offset]);
  }
}