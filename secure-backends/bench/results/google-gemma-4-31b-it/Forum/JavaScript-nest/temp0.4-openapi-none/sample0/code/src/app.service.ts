import { Injectable, OnModuleInit } from '@nestjs/common';
import { open } from 'sqlite';
import sqlite3 from 'sqlite3';

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
        username TEXT NOT NULL,
        content TEXT NOT NULL,
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

  async getMessages(limit: number, offset: number, sort: 'ASC' | 'DESC') {
    const messages = await this.db.all(
      `SELECT username, content, created_at FROM messages 
       ORDER BY created_at ${sort} 
       LIMIT ? OFFSET ?`,
      [limit, offset],
    );

    return this.renderHtml(messages);
  }

  private renderHtml(messages: any[]) {
    const rows = messages
      .map(
        (m) => `
      <div style="border: 1px solid #ccc; margin: 10px; padding: 10px; border-radius: 5px;">
        <strong>${this.escapeHtml(m.username)}</strong> 
        <small style="color: gray;">${m.created_at}</small>
        <p>${this.escapeHtml(m.content)}</p>
      </div>`,
      )
      .join('');

    return `
      <!DOCTYPE html>
      <html>
        <head><title>MyForum</title></head>
        <body style="font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px;">
          <h1>MyForum</h1>
          <form action="/messages" method="POST" style="margin-bottom: 30px; padding: 15px; background: #f4f4f4; border-radius: 5px;">
            <input type="text" name="username" placeholder="Username" required /><br><br>
            <textarea name="content" placeholder="Message" required style="width: 100%"></textarea><br><br>
            <button type="submit">Post Message</button>
          </form>
          <hr>
          <div>${rows || '<p>No messages yet!</p>'}</div>
        </body>
      </html>
    `;
  }

  private escapeHtml(text: string) {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }
}