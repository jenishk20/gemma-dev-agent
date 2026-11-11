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
    const emailRegex = /From:.*<(.+?)>|From:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/;
    const match = rawEmail.match(emailRegex);
    const email = match ? (match[1] || match[2]) : 'unknown';

    // Check if any keyword exists in the raw email text (case-insensitive)
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