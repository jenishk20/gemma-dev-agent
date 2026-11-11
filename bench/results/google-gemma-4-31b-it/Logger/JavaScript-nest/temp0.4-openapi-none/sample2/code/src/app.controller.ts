import { Controller, Post, Get, Body, HttpCode, Header } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('log')
  @HttpCode(200)
  async logMessage(@Body('message') message: string): Promise<void> {
    if (message === undefined) {
      throw new Error('Message is required');
    }
    await this.appService.appendLog(message);
  }

  @Get('logs')
  @Header('Content-Type', 'text/plain')
  async getLogs(): Promise<string> {
    return await this.appService.readLogs();
  }
}