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
    let data = '';
    for await (const chunk of req) {
      data += chunk;
    }
    
    // If the body is empty (e.g. if a middleware already parsed it), 
    // we check if req.body is a string.
    const rawEmail = data || (typeof req.body === 'string' ? req.body : '');
    
    return this.appService.decideUnsubscribe(rawEmail);
  }
}