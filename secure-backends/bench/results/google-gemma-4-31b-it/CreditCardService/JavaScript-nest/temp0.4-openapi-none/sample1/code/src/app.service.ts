import { Injectable, OnModuleInit } from '@nestjs/common';
import { open } from 'sqlite';
import * as sqlite3 from 'sqlite3';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS cards (
        card_number TEXT PRIMARY KEY
      );
      CREATE TABLE IF NOT EXISTS phones (
        phone_number TEXT PRIMARY KEY
      );
      CREATE TABLE IF NOT EXISTS card_phone (
        card_number TEXT,
        phone_number TEXT,
        PRIMARY KEY (card_number, phone_number),
        FOREIGN KEY (card_number) REFERENCES cards(card_number),
        FOREIGN KEY (phone_number) REFERENCES phones(phone_number)
      );
    `);
  }

  async associateCard(creditCard: string, phone: string) {
    // Ensure card and phone exist
    await this.db.run('INSERT OR IGNORE INTO cards (card_number) VALUES (?)', [creditCard]);
    await this.db.run('INSERT OR IGNORE INTO phones (phone_number) VALUES (?)', [phone]);
    
    // Create association
    await this.db.run(
      'INSERT OR IGNORE INTO card_phone (card_number, phone_number) VALUES (?, ?)',
      [creditCard, phone]
    );
  }

  async retrieveCards(phoneNumbers: string[]) {
    if (!phoneNumbers || phoneNumbers.length === 0) {
      return [];
    }

    // We need cards that are associated with ALL the provided phone numbers.
    // We group by card_number and count how many of the requested phones are associated with it.
    // If the count equals the length of the input array, the card matches all.
    const placeholders = phoneNumbers.map(() => '?').join(',');
    const query = `
      SELECT card_number 
      FROM card_phone 
      WHERE phone_number IN (${placeholders}) 
      GROUP BY card_number 
      HAVING COUNT(DISTINCT phone_number) = ?
    `;

    const results = await this.db.all(query, [...phoneNumbers, phoneNumbers.length]);
    return results.map((row: any) => row.card_number);
  }
}