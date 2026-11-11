import { Injectable, OnModuleInit } from '@nestjs/common';
import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

@Injectable()
export class AppService implements OnModuleInit {
  private db: any;

  async onModuleInit() {
    this.db = await open({
      filename: 'db.sqlite3',
      driver: sqlite3.Database,
    });

    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS card_phone_associations (
        credit_card TEXT,
        phone TEXT,
        PRIMARY KEY (credit_card, phone)
      );
    `);
  }

  async associateCard(creditCard: string, phone: string): Promise<void> {
    await this.db.run(
      'INSERT OR IGNORE INTO card_phone_associations (credit_card, phone) VALUES (?, ?)',
      [creditCard, phone],
    );
  }

  async retrieveCards(phoneNumbers: string[]): Promise<string[]> {
    if (!phoneNumbers || phoneNumbers.length === 0) {
      return [];
    }

    // We look for cards that are associated with any of the target phones,
    // then group by card and filter for those that have a count equal to the number of target phones.
    // This ensures the card is associated with ALL provided phone numbers.
    const placeholders = phoneNumbers.map(() => '?').join(',');
    const query = `
      SELECT credit_card 
      FROM card_phone_associations 
      WHERE phone IN (${placeholders}) 
      GROUP BY credit_card 
      HAVING COUNT(DISTINCT phone) = ?
    `;

    const rows = await this.db.all(query, [...phoneNumbers, phoneNumbers.length]);
    return rows.map((row: any) => row.credit_card);
  }
}