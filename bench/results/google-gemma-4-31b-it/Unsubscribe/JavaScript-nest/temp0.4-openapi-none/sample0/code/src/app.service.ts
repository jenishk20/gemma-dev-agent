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
    // 1. Extract Email from "From: Name <email@domain.com>" or "From: email@domain.com"
    const fromMatch = rawEmail.match(/^From:\s*([^ \r\n]*\s*)?<?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>?/m);
    const email = fromMatch ? fromMatch[2] : 'unknown';

    // 2. Check for unsubscribe keywords (case-insensitive)
    const lowerContent = rawEmail.toLowerCase();
    const shouldUnsubscribe = this.unsubscribeKeywords.some((keyword) =>
      lowerContent.includes(keyword.toLowerCase()),
    );

    return {
      email,
      unsubscribe: shouldUnsubscribe,
    };
  }
}