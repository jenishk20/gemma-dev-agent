import { Controller, Post, Body, Req } from '@nestjs/common';
import { Request } from 'express';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('decideUnsubscribe')
  async decideUnsubscribe(@Req() req: Request): Promise<{ email: string; unsubscribe: boolean }> {
    // Since the OpenAPI spec defines the request body as text/plain, 
    // we read the raw body from the request stream.
    let rawBody = '';
    
    // Express by default might not parse text/plain into req.body unless configured.
    // We handle the raw body reading here.
    if (typeof req.body === 'string') {
      rawBody = req.body;
    } else {
      // Fallback for cases where body is not pre-parsed as string
      const chunks = [];
      for await (const chunk of req) {
        chunks.push(chunk);
      }
      rawBody = Buffer.concat(chunks).toString('utf-8');
    }

    return this.appService.decideUnsubscribe(rawBody);
  }
}