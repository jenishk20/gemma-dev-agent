import { Injectable, OnModuleInit } from '@nestjs/common';
import { open } from 'sqlite';
import { Database } from 'sqlite3';

export interface Message {
  content: string;
  username: string;
}

@Injectable()
export class AppService implements OnModuleInit {
  private db!: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: Database,
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

  async createMessage(message: Message) {
    await this.db.run(
      'INSERT INTO messages (username, content) VALUES (?, ?)',
      [message.username, message.content],
    );
  }

  async getMessagesHtml(limit: number, offset: number, sort: string): Promise<string> {
    const order = sort.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';
    const messages = await this.db.all(
      `SELECT username, content, created_at FROM messages ORDER BY created_at ${order} LIMIT ? OFFSET ?`,
      [limit, offset],
    );

    const messagesHtml = messages
      .map(
        (m: any) => `
        <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
          <strong>${this.escapeHtml(m.username)}</strong> <small>${m.created_at}</small><br/>
          <p>${this.escapeHtml(m.content)}</p>
        </div>`,
      )
      .join('');

    return `
      <!DOCTYPE html>
      <html>
        <head><title>MyForum</title></head>
        <body style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px;">
          <h1>MyForum</h1>
          <form action="/messages" method="POST" style="margin-bottom: 30px;">
            <input type="text" name="username" placeholder="Username" required /><br/><br/>
            <textarea name="content" placeholder="Message" required style="width: 100%"></textarea><br/><br/>
            <button type="submit">Post Message</button>
          </form>
          <hr/>
          <h2>Messages</h2>
          ${messagesHtml || '<p>No messages yet.</p>'}
        </body>
      </html>
    `;
  }

  private escapeHtml(unsafe: string) {
    return unsafe
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}