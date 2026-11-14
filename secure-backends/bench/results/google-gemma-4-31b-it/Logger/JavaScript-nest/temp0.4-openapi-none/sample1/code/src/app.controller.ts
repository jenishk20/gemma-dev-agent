import { Controller, Post, Get, Body, HttpCode, HttpStatus, Header } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('log')
  @HttpCode(HttpStatus.OK)
  async logMessage(@Body() body: { message: string }) {
    if (body && body.message) {
      await this.appService.addLog(body.message);
    }
    return {};
  }

  @Get('logs')
  @Header('Content-Type', 'text/plain')
  @HttpCode(HttpStatus.OK)
  async retrieveLogs(): Promise<string> {
    return await this.appService.getLogs();
  }
}