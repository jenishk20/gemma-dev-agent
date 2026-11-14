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
    `);
  }

  async getAllEntriesHtml(): Promise<string> {
    const entries = await this.db.all('SELECT id, title FROM entries');
    const listItems = entries
      .map(e => `<li><a href="/entries/${e.id}">${e.title}</a></li>`)
      .join('');
    
    return `
      <html>
        <body>
          <h1>Wiki Entries</h1>
          <ul>${listItems || '<li>No entries yet.</li>'}</ul>
          <hr/>
          <h3>Create New Entry</h3>
          <form action="/entries" method="POST">
            <input name="title" placeholder="Title" required /><br/>
            <textarea name="content" placeholder="Content" required></textarea><br/>
            <input name="createdBy" placeholder="Your Name" required /><br/>
            <button type="submit">Create</button>
          </form>
        </body>
      </html>
    `;
  }

  async createEntry(data: { title: string, content: string, createdBy: string }) {
    const id = uuidv4();
    const now = new Date().toISOString();
    await this.db.run(
      'INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.title, data.content, data.createdBy, now]
    );
    await this.db.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.content, data.createdBy, 'Initial creation', now]
    );
    return { id, ...data, lastModifiedBy: data.createdBy, lastModifiedAt: now };
  }

  async getEntryHtml(id: string): Promise<string> {
    const entry = await this.db.get('SELECT * FROM entries WHERE id = ?', [id]);
    if (!entry) throw new NotFoundException('Entry not found');

    const contributors = await this.db.all('SELECT DISTINCT modifiedBy FROM edits WHERE entryId = ?', [id]);
    const contributorList = contributors.map(c => c.modifiedBy).join(', ');

    return `
      <html>
        <body>
          <h1>${entry.title}</h1>
          <div style="border: 1px solid #ccc; padding: 10px; white-space: pre-wrap;">${entry.content}</div>
          <p><i>Last modified by ${entry.lastModifiedBy} on ${entry.lastModifiedAt}</i></p>
          <p><b>Contributors:</b> ${contributorList}</p>
          <hr/>
          <a href="/entries/${id}/edits">View History</a> | <a href="/entries">Back to Home</a>
          <h3>Edit Entry</h3>
          <form action="/entries/${id}" method="POST">
            <textarea name="content" style="width: 100%; height: 200px;">${entry.content}</textarea><br/>
            <input name="modifiedBy" placeholder="Your Name" required /><br/>
            <input name="summary" placeholder="Edit summary" required /><br/>
            <button type="submit">Update</button>
          </form>
        </body>
      </html>
    `;
  }

  async updateEntry(id: string, data: { content: string, modifiedBy: string, summary: string }) {
    const entry = await this.db.get('SELECT * FROM entries WHERE id = ?', [id]);
    if (!entry) throw new NotFoundException('Entry not found');

    const now = new Date().toISOString();
    await this.db.run(
      'UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?',
      [data.content, data.modifiedBy, now, id]
    );
    await this.db.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.content, data.modifiedBy, data.summary, now]
    );

    return { ...entry, content: data.content, lastModifiedBy: data.modifiedBy, lastModifiedAt: now };
  }

  async getEditsHtml(id: string): Promise<string> {
    const entry = await this.db.get('SELECT * FROM entries WHERE id = ?', [id]);
    if (!entry) throw new NotFoundException('Entry not found');

    const edits = await this.db.all('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [id]);
    
    const editRows = edits.map((edit, index) => {
      const prevEdit = edits[index + 1];
      const diff = prevEdit ? `Diff: Changed from "${prevEdit.content.substring(0, 20)}..." to "${edit.content.substring(0, 20)}..."` : 'Initial version';
      return `<li><b>${edit.modifiedAt}</b> by ${edit.modifiedBy}: ${edit.summary} <br/> <small>${diff}</small></li>`;
    }).join('');

    return `
      <html>
        <body>
          <h1>History for ${entry.title}</h1>
          <ul>${editRows}</ul>
          <a href="/entries/${id}">Back to Entry</a>
        </body>
      </html>
    `;
  }
}