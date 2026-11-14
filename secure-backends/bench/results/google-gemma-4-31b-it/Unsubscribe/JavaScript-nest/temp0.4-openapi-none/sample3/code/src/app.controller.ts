import { Controller, Post, Body, Req } from '@nestjs/common';
import { AppService } from './app.service';
import { Request } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('decideUnsubscribe')
  async decideUnsubscribe(@Req() req: Request) {
    // Since the OpenAPI spec defines the request body as text/plain,
    // we read the raw body from the request.
    // Note: In a production NestJS app, you might need a custom middleware 
    // or raw-body parser to handle text/plain if the default body-parser 
    // doesn't populate req.body for non-JSON types.
    
    let rawBody = '';
    if (typeof req.body === 'string') {
      rawBody = req.body;
    } else if (req.body && typeof req.body === 'object') {
      // Handle cases where express might have parsed it as an object or empty
      rawBody = JSON.stringify(req.body);
    }

    // Fallback for raw text buffers if the body is not automatically parsed
    if (!rawBody && req['body'] === undefined) {
       // This is a simplified approach for the provided environment
       rawBody = ''; 
    }

    // If the body is sent as text/plain, Express usually puts it in req.body 
    // if the text parser is enabled. For this implementation, we assume 
    // the standard Nest/Express setup.
    const content = (req.body as string) || '';
    
    return this.appService.decideUnsubscribe(content);
  }
}