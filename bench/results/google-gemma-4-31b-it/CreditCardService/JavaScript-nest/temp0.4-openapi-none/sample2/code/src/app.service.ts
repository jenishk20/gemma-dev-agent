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
      CREATE TABLE IF NOT EXISTS card_phone_association (
        credit_card TEXT,
        phone TEXT,
        PRIMARY KEY (credit_card, phone)
      )
    `);
  }

  async associateCard(creditCard: string, phone: string) {
    await this.db.run(
      'INSERT OR IGNORE INTO card_phone_association (credit_card, phone) VALUES (?, ?)',
      [creditCard, phone]
    );
  }

  async retrieveCards(phoneNumbers: string[]) {
    if (!phoneNumbers || phoneNumbers.length === 0) {
      return [];
    }

    // We need cards that are associated with ALL provided phone numbers.
    // We filter for the provided phones, group by card, and ensure the count matches.
    const placeholders = phoneNumbers.map(() => '?').join(',');
    const query = `
      SELECT credit_card 
      FROM card_phone_association 
      WHERE phone IN (${placeholders}) 
      GROUP BY credit_card 
      HAVING COUNT(DISTINCT phone) = ?
    `;

    const params = [...phoneNumbers, phoneNumbers.length];
    const rows = await this.db.all(query, params);
    return rows.map(row => row.credit_card);
  }
}