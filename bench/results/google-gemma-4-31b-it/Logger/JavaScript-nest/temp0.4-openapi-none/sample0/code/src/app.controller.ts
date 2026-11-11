import { Controller, Post, Get, Body, HttpCode, HttpStatus, Header } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('/log')
  @HttpCode(HttpStatus.OK)
  async createLog(@Body() body: { message: string }) {
    if (body && body.message) {
      await this.appService.logMessage(body.message);
    }
    return {};
  }

  @Get('/logs')
  @HttpCode(HttpStatus.OK)
  @Header('Content-Type', 'text/plain')
  async retrieveLogs() {
    return await this.appService.getLogs();
  }
}