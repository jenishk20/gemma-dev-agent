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
    const fromMatch = rawEmail.match(/From:.*<([^>]+)>/) || rawEmail.match(/From:\s*([^\s\r\n]+)/);
    const email = fromMatch ? fromMatch[1].trim() : 'unknown';

    // Check if any keyword exists in the raw email text (case-insensitive)
    const lowerEmail = rawEmail.toLowerCase();
    const shouldUnsubscribe = this.unsubscribeKeywords.some((keyword) => 
      lowerEmail.includes(keyword.toLowerCase())
    );

    return {
      email,
      unsubscribe: shouldUnsubscribe,
    };
  }
}