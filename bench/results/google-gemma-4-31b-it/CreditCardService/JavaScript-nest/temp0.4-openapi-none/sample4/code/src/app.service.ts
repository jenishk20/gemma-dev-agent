import { Injectable, OnModuleInit } from '@nestjs/common';
import { open } from 'sqlite';
import { Database } from 'sqlite3';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_number TEXT UNIQUE
      );
      CREATE TABLE IF NOT EXISTS phones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone_number TEXT UNIQUE
      );
      CREATE TABLE IF NOT EXISTS card_phone (
        card_id INTEGER,
        phone_id INTEGER,
        PRIMARY KEY (card_id, phone_id),
        FOREIGN KEY (card_id) REFERENCES cards(id),
        FOREIGN KEY (phone_id) REFERENCES phones(id)
      );
    `);
  }

  async associateCard(creditCard: string, phone: string) {
    // Ensure card exists and get ID
    await this.db.run('INSERT OR IGNORE INTO cards (card_number) VALUES (?)', [creditCard]);
    const cardRow = await this.db.get('SELECT id FROM cards WHERE card_number = ?', [creditCard]);
    
    // Ensure phone exists and get ID
    await this.db.run('INSERT OR IGNORE INTO phones (phone_number) VALUES (?)', [phone]);
    const phoneRow = await this.db.get('SELECT id FROM phones WHERE phone_number = ?', [phone]);

    // Create association
    await this.db.run('INSERT OR IGNORE INTO card_phone (card_id, phone_id) VALUES (?, ?)', [cardRow.id, phoneRow.id]);
  }

  async retrieveCards(phoneNumbers: string[]) {
    if (!phoneNumbers || phoneNumbers.length === 0) {
      return [];
    }

    // We need cards that are associated with ALL the provided phone numbers.
    // We join cards with the association table, filter by the list of phones, 
    // and group by card_id, ensuring the count of distinct phones matches the input list size.
    const placeholders = phoneNumbers.map(() => '?').join(',');
    const query = `
      SELECT c.card_number 
      FROM cards c
      JOIN card_phone cp ON c.id = cp.card_id
      JOIN phones p ON p.id = cp.phone_id
      WHERE p.phone_number IN (${placeholders})
      GROUP BY c.id
      HAVING COUNT(DISTINCT p.phone_number) = ?
    `;

    const rows = await this.db.all(query, [...phoneNumbers, phoneNumbers.length]);
    return rows.map(row => row.card_number);
  }
}