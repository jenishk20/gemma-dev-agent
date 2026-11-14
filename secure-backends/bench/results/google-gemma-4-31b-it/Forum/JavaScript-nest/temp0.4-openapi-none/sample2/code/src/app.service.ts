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
      CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  async createMessage(username: string, content: string) {
    await this.db.run(
      'INSERT INTO messages (username, content) VALUES (?, ?)',
      [username, content],
    );
  }

  async getMessagesHtml(limit: number, offset: number, sort: string) {
    const order = sort.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';
    const messages = await this.db.all(
      `SELECT username, content, created_at FROM messages ORDER BY created_at ${order} LIMIT ? OFFSET ?`,
      [limit, offset],
    );

    const listItems = messages
      .map(m => `<li><strong>${this.escapeHtml(m.username)}</strong> (${m.created_at}): ${this.escapeHtml(m.content)}</li>`)
      .join('');

    return `
      <!DOCTYPE html>
      <html>
        <head><title>MyForum</title></head>
        <body>
          <h1>Forum Messages</h1>
          <ul>${listItems || '<li>No messages yet.</li>'}</ul>
          <hr/>
          <h3>Post a Message</h3>
          <form action="/messages" method="POST">
            <input type="text" name="username" placeholder="Username" required /><br/>
            <textarea name="content" placeholder="Message" required></textarea><br/>
            <button type="submit">Post</button>
          </form>
        </body>
      </html>
    `;
  }

  private escapeHtml(text: string) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }
}