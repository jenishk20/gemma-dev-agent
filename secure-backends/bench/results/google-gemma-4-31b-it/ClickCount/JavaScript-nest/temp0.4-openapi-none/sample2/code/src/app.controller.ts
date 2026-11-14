import { Controller, Post, Get, Query, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('click')
  @HttpCode(HttpStatus.CREATED)
  async registerClick() {
    await this.appService.registerClick();
    return { message: 'Click registered successfully' };
  }

  @Get('clicks')
  async getClicks(
    @Query('date') date: string,
    @Query('direction') direction: string,
  ) {
    return this.appService.getClicks(date, direction);
  }
}