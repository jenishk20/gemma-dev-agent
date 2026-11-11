import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('decideUnsubscribe')
  @HttpCode(HttpStatus.OK)
  decideUnsubscribe(@Body() rawEmail: string) {
    // NestJS by default parses bodies. Since the OpenAPI specifies text/plain,
    // the body will arrive as a string if the Content-Type is text/plain.
    return this.appService.decideUnsubscribe(rawEmail);
  }
}