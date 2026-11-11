import { Controller, Post, Get, Body, HttpCode, Header } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('log')
  @HttpCode(200)
  async log(@Body('message') message: string) {
    await this.appService.logMessage(message);
    return;
  }

  @Get('logs')
  @Header('Content-Type', 'text/plain')
  async getLogs() {
    return await this.appService.getLogs();
  }
}