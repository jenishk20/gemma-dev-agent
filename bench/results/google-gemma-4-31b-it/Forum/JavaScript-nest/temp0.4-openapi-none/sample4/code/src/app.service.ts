import { Injectable, OnModuleInit } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { promisify } from 'util';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;
  private run = promisify(this.db?.run.bind(this.db));
  private all = promisify(this.db?.all.bind(this.db));

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    
    // Re-bind promisified methods after db is initialized
    this.run = promisify(this.db.run.bind(this.db));
    this.all = promisify(this.db.all.bind(this.db));

    await this.run(`
      CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  async createMessage(username: string, content: string) {
    await this.run(
      'INSERT INTO messages (username, content) VALUES (?, ?)',
      [username, content]
    );
  }

  async getMessages(limit: number, offset: number, sort: 'ASC' | 'DESC') {
    const query = `
      SELECT username, content, created_at 
      FROM messages 
      ORDER BY created_at ${sort} 
      LIMIT ? OFFSET ?
    `;
    return await this.all(query, [limit, offset]);
  }
}