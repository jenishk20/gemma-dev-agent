import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    
    const initDb = `
      CREATE TABLE IF NOT EXISTS entries (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT,
        lastModifiedBy TEXT,
        lastModifiedAt TEXT
      );
      CREATE TABLE IF NOT EXISTS edits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entryId TEXT,
        content TEXT,
        modifiedBy TEXT,
        summary TEXT,
        modifiedAt TEXT,
        FOREIGN KEY(entryId) REFERENCES entries(id)
      );
    `;

    return new Promise((resolve, reject) => {
      this.db.exec(initDb, (err) => {
        if (err) reject(err);
        else resolve(null);
      });
    });
  }

  private query<T>(sql: string, params: any[] = []): Promise<T[]> {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }

  private run(sql: string, params: any[] = []): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function(err) {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  async getAllEntriesHtml(): Promise<string> {
    const entries = await this.query('SELECT id, title FROM entries');
    const list = entries.map(e => `<li><a href="/entries/${e.id}">${e.title}</a></li>`).join('');
    return `<html><body><h1>Wiki Entries</h1><ul>${list}</ul><p><a href="/create">Create New Entry</a></p></body></html>`;
  }

  async createEntry(data: { title: string, content: string, createdBy: string }) {
    const id = uuidv4();
    const now = new Date().toISOString();
    await this.run(
      'INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.title, data.content, data.createdBy, now]
    );
    await this.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.content, data.createdBy, 'Initial creation', now]
    );
    return { id, ...data, lastModifiedBy: data.createdBy, lastModifiedAt: now };
  }

  async getEntryHtml(id: string): Promise<string> {
    const entry = await this.query('SELECT * FROM entries WHERE id = ?', [id]);
    if (entry.length === 0) throw new NotFoundException();
    
    const e = entry[0];
    const contributors = await this.query('SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?', [id]);
    const contributorList = contributors.map(c => c.modifiedBy).join(', ');

    return `
      <html>
        <body>
          <h1>${e.title}</h1>
          <div style="border:1px solid #ccc; padding:10px; margin:10px 0;">${e.content}</div>
          <p>Last modified by: ${e.lastModifiedBy} at ${e.lastModifiedAt}</p>
          <p>Contributors: ${contributorList}</p>
          <hr/>
          <a href="/entries">Back to List</a> | <a href="/entries/${id}/edits">View History</a>
        </body>
      </html>`;
  }

  async updateEntry(id: string, data: { content: string, modifiedBy: string, summary: string }) {
    const entry = await this.query('SELECT * FROM entries WHERE id = ?', [id]);
    if (entry.length === 0) throw new NotFoundException();

    const now = new Date().toISOString();
    await this.run(
      'UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?',
      [data.content, data.modifiedBy, now, id]
    );
    await this.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.content, data.modifiedBy, data.summary, now]
    );

    const updated = await this.query('SELECT * FROM entries WHERE id = ?', [id]);
    return updated[0];
  }

  async getEditsHtml(id: string): Promise<string> {
    const entry = await this.query('SELECT * FROM entries WHERE id = ?', [id]);
    if (entry.length === 0) throw new NotFoundException();

    const edits = await this.query('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [id]);
    const rows = edits.map(e => `
      <tr>
        <td>${e.modifiedAt}</td>
        <td>${e.modifiedBy}</td>
        <td>${e.summary}</td>
        <td><pre>${e.content}</pre></td>
      </tr>
    `).join('');

    return `
      <html>
        <body>
          <h1>Edit History for ${entry[0].title}</h1>
          <table border="1">
            <thead><tr><th>Date</th><th>User</th><th>Summary</th><th>Content</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
          <p><a href="/entries/${id}">Back to Entry</a></p>
        </body>
      </html>`;
  }
}