import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller('calculator')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post()
  calculate(@Body() body: { expression: string }) {
    if (!body || typeof body.expression !== 'string') {
      throw new BadRequestException('Invalid input');
    }
    
    const result = this.appService.calculate(body.expression);
    return { result };
  }
}