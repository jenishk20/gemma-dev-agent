import { Controller, Post, Body, Req } from '@nestjs/common';
import { AppService } from './app.service';
import { Request } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('decideUnsubscribe')
  async decideUnsubscribe(@Req() req: Request): Promise<{ email: string; unsubscribe: boolean }> {
    // Since the OpenAPI spec defines the request body as text/plain, 
    // we read the raw body from the request stream.
    let body = '';
    for await (const chunk of req) {
      body += chunk;
    }
    
    // If the body is empty (e.g. due to middleware already parsing it), 
    // we check the req.body property.
    const rawEmail = body || (typeof req.body === 'string' ? req.body : JSON.stringify(req.body));

    return this.appService.decideUnsubscribe(rawEmail);
  }
}