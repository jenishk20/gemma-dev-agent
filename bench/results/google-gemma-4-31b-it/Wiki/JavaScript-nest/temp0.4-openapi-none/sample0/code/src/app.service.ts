import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class AppService implements OnModuleInit {
  private db: sqlite3.Database;

  async onModuleInit() {
    this.db = new sqlite3.Database('db.sqlite3');
    this.db.serialize(() => {
      this.db.run(`
        CREATE TABLE IF NOT EXISTS entries (
          id TEXT PRIMARY KEY,
          title TEXT,
          content TEXT,
          lastModifiedBy TEXT,
          lastModifiedAt TEXT
        )
      `);
      this.db.run(`
        CREATE TABLE IF NOT EXISTS edits (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          entryId TEXT,
          content TEXT,
          modifiedBy TEXT,
          summary TEXT,
          modifiedAt TEXT,
          FOREIGN KEY(entryId) REFERENCES entries(id)
        )
      `);
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
    const entries = await this.query<any>('SELECT id, title FROM entries');
    let html = '<h1>Wiki Entries</h1><ul>';
    if (entries.length === 0) {
      html += '<li>No entries found.</li>';
    } else {
      entries.forEach(e => {
        html += `<li><a href="/entries/${e.id}">${e.title}</a></li>`;
      });
    }
    html += '</ul><p><a href="/create">Create New Entry</a></p>';
    return html;
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
    const entry = await this.query<any>('SELECT * FROM entries WHERE id = ?', [id]);
    if (entry.length === 0) throw new NotFoundException('Entry not found');
    
    const e = entry[0];
    const contributors = await this.query<any>('SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?', [id]);
    const contributorList = contributors.map(c => c.modifiedBy).join(', ');

    return `
      <h1>${e.title}</h1>
      <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0;">
        ${e.content.replace(/\n/g, '<br>')}
      </div>
      <p><strong>Last Modified:</strong> ${e.lastModifiedAt} by ${e.lastModifiedBy}</p>
      <p><strong>Contributors:</strong> ${contributorList}</p>
      <hr>
      <a href="/entries">Back to List</a> | <a href="/entries/${id}/edits">View History</a>
    `;
  }

  async updateEntry(id: string, data: { content: string, modifiedBy: string, summary: string }) {
    const entry = await this.query<any>('SELECT * FROM entries WHERE id = ?', [id]);
    if (entry.length === 0) throw new NotFoundException('Entry not found');

    const now = new Date().toISOString();
    await this.run(
      'UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?',
      [data.content, data.modifiedBy, now, id]
    );
    await this.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.content, data.modifiedBy, data.summary, now]
    );

    return { id, title: entry[0].title, content: data.content, lastModifiedBy: data.modifiedBy, lastModifiedAt: now };
  }

  async getEditsHtml(id: string): Promise<string> {
    const entry = await this.query<any>('SELECT title FROM entries WHERE id = ?', [id]);
    if (entry.length === 0) throw new NotFoundException('Entry not found');

    const edits = await this.query<any>('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [id]);
    
    let html = `<h1>Edit History: ${entry[0].title}</h1><table border="1"><tr><th>Date</th><th>User</th><th>Summary</th><th>Content Snippet</th></tr>`;
    
    edits.forEach((edit, index) => {
      html += `<tr>
        <td>${edit.modifiedAt}</td>
        <td>${edit.modifiedBy}</td>
        <td>${edit.summary}</td>
        <td><code>${edit.content.substring(0, 50)}...</code></td>
      </tr>`;
    });
    
    html += '</table><br><a href="/entries/' + id + '">Back to Entry</a>';
    return html;
  }
}