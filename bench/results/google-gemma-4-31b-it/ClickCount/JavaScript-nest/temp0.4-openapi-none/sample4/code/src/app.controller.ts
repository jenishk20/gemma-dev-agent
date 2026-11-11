import { Controller, Post, Get, Query, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('click')
  @HttpCode(HttpStatus.CREATED)
  async registerClick() {
    return await this.appService.registerClick();
  }

  @Get('clicks')
  async getClicks(
    @Query('date') date: string,
    @Query('direction') direction: string,
  ) {
    return await this.appService.getClicks(date, direction);
  }
}