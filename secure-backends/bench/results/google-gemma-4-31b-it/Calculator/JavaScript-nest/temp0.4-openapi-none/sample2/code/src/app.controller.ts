import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller('calculator')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post()
  @HttpCode(HttpStatus.OK)
  calculate(@Body() body: { expression: string }) {
    if (!body || typeof body.expression !== 'string') {
      // This will trigger a 400 Bad Request via the service or manual check
      throw new Error('Expression is required');
    }
    
    const result = this.appService.calculate(body.expression);
    return { result };
  }
}