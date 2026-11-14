import { Injectable, OnModuleInit, NotFoundException } from '@nestjs/common';
import * as sqlite3 from 'sqlite3';
import { open } from 'sqlite';
import { v4 as uuidv4 } from 'uuid';

export interface Entry {
  id: string;
  title: string;
  content: string;
  lastModifiedBy: string;
  lastModifiedAt: string;
}

export interface NewEntry {
  title: string;
  content: string;
  createdBy: string;
}

export interface UpdateEntry {
  content: string;
  modifiedBy: string;
  summary: string;
}

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

  async getAllEntries(): Promise<Entry[]> {
    return await this.db.all('SELECT * FROM entries');
  }

  async createEntry(data: NewEntry): Promise<Entry> {
    const id = uuidv4();
    const now = new Date().toISOString();
    const entry: Entry = {
      id,
      title: data.title,
      content: data.content,
      lastModifiedBy: data.createdBy,
      lastModifiedAt: now,
    };

    await this.db.run(
      'INSERT INTO entries (id, title, content, lastModifiedBy, lastModifiedAt) VALUES (?, ?, ?, ?, ?)',
      [entry.id, entry.title, entry.content, entry.lastModifiedBy, entry.lastModifiedAt]
    );

    await this.db.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.content, data.createdBy, 'Initial creation', now]
    );

    return entry;
  }

  async getEntry(id: string): Promise<Entry> {
    const entry = await this.db.get('SELECT * FROM entries WHERE id = ?', [id]);
    if (!entry) throw new NotFoundException('Entry not found');
    return entry;
  }

  async updateEntry(id: string, data: UpdateEntry): Promise<Entry> {
    const entry = await this.getEntry(id);
    const now = new Date().toISOString();

    await this.db.run(
      'UPDATE entries SET content = ?, lastModifiedBy = ?, lastModifiedAt = ? WHERE id = ?',
      [data.content, data.modifiedBy, now, id]
    );

    await this.db.run(
      'INSERT INTO edits (entryId, content, modifiedBy, summary, modifiedAt) VALUES (?, ?, ?, ?, ?)',
      [id, data.content, data.modifiedBy, data.summary, now]
    );

    return {
      id: entry.id,
      title: entry.title,
      content: data.content,
      lastModifiedBy: data.modifiedBy,
      lastModifiedAt: now,
    };
  }

  async getEdits(id: string) {
    const entry = await this.getEntry(id);
    const edits = await this.db.all('SELECT * FROM edits WHERE entryId = ? ORDER BY modifiedAt DESC', [id]);
    return { entry, edits };
  }
}