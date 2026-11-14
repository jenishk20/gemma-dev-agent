import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
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
      CREATE TABLE IF NOT EXISTS entries (
        id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        lastModifiedBy TEXT,
        lastModifiedAt DATETIME
      );
      CREATE TABLE IF NOT EXISTS edits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entryId TEXT,
        content TEXT,
        modifiedBy TEXT,
        summary TEXT,
        modifiedAt DATETIME,
        FOREIGN KEY(entryId) REFERENCES entries(id)
      );
    `);
  }

  async getAllEntries() {
    const entries = await this.db.all('SELECT id, title FROM entries');
    let html = '<h1>Wiki Entries</h1><ul>';
    entries.forEach(e => {
      html += `<li><a href="/entries/${e.id}">${e.title}</a></li>`;
    });
    html += '</ul><hr><p>Create new entry via POST /entries</p>';
    return html;
  }

  async createEntry(dto: { title: string, content: string, createdBy: string }) {
    const id = uuidv4();
    const now = new Date().toISOString();
    await this.db.run(
      'INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, dto.title, dto.content, dto.createdBy, now]
    );
    await this.db.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, dto.content, dto.createdBy, 'Initial creation', now]
    );
    return { id, ...dto, lastModifiedBy: dto.createdBy, lastModifiedAt: now };
  }

  async getEntry(id: string) {
    const entry = await this.db.get('SELECT * FROM entries WHERE id = ?', [id]);
    if (!entry) throw new NotFoundException('Entry not found');

    const contributors = await this.db.all('SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?', [id]);
    const contributorList = contributors.map(c => c.modifiedBy).join(', ');

    return `
      <h1>${entry.title}</h1>
      <p><strong>Last Modified:</strong> ${entry.lastModifiedAt} by ${entry.lastModifiedBy}</p>
      <p><strong>Contributors:</strong> ${contributorList}</p>
      <hr>
      <div>${entry.content}</div>
      <hr>
      <a href="/entries/${id}/edits">View History</a> | <a href="/entries">Back to List</a>
    `;
  }

  async updateEntry(id: string, dto: { content: string, modifiedBy: string, summary: string }) {
    const entry = await this.db.get('SELECT * FROM entries WHERE id = ?', [id]);
    if (!entry) throw new NotFoundException('Entry not found');

    const now = new Date().toISOString();
    await this.db.run(
      'UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?',
      [dto.content, dto.modifiedBy, now, id]
    );
    await this.db.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, dto.content, dto.modifiedBy, dto.summary, now]
    );

    return { ...entry, content: dto.content, lastModifiedBy: dto.modifiedBy, lastModifiedAt: now };
  }

  async getEdits(id: string) {
    const entry = await this.db.get('SELECT * FROM entries WHERE id = ?', [id]);
    if (!entry) throw new NotFoundException('Entry not found');

    const edits = await this.db.all('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [id]);
    
    let html = `<h1>History for ${entry.title}</h1><table border="1"><tr><th>Date</th><th>User</th><th>Summary</th><th>Content</th></tr>`;
    edits.forEach(e => {
      html += `<tr><td>${e.modifiedAt}</td><td>${e.modifiedBy}</td><td>${e.summary}</td><td>${e.content}</td></tr>`;
    });
    html += '</table><br><a href="/entries/' + id + '">Back to Entry</a>';
    return html;
  }
}