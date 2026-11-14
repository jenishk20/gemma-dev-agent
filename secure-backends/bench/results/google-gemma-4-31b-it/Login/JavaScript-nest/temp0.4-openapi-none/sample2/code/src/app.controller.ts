import { Controller, Post, Body } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('register')
  async register(@Body() body: any) {
    return this.appService.register(body);
  }

  @Post('login')
  async login(@Body() body: any) {
    return this.appService.login(body);
  }
}