import { Injectable } from '@nestjs/common';

@Injectable()
export class AppService {
  private readonly unsubscribeKeywords = [
    'unsubscribe',
    'remove me',
    'deregister me',
    'stop sending me',
    'delete me',
  ];

  decideUnsubscribe(rawEmail: string): { email: string; unsubscribe: boolean } {
    // Extract email from "From: Name <email@domain.com>" or "From: email@domain.com"
    const fromMatch = rawEmail.match(/^From:\s*.*?(?:<([^>]+)>|(\S+@\S+))/mi);
    const email = fromMatch ? (fromMatch[1] || fromMatch[2]) : 'unknown';

    // Normalize text to lowercase for keyword matching
    const lowerEmail = rawEmail.toLowerCase();
    const shouldUnsubscribe = this.unsubscribeKeywords.some((keyword) =>
      lowerEmail.includes(keyword),
    );

    return {
      email,
      unsubscribe: shouldUnsubscribe,
    };
  }
}