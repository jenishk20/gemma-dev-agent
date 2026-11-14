import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

interface CalculateRequest {
  expression: string;
}

interface CalculateResponse {
  result: string;
}

@Controller('calculator')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post()
  calculate(@Body() body: CalculateRequest): CalculateResponse {
    if (!body || typeof body.expression !== 'string') {
      throw new BadRequestException('Invalid input: expression is required and must be a string');
    }
    
    const result = this.appService.calculate(body.expression);
    return { result };
  }
}