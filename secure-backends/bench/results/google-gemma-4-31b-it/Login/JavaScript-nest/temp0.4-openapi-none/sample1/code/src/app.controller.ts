import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('register')
  @HttpCode(HttpStatus.CREATED)
  async register(@Body() body: { email: string, password: string, name: string }) {
    return this.appService.register(body.email, body.password, body.name);
  }

  @Post('login')
  @HttpCode(HttpStatus.OK)
  async login(@Body() body: { email: string, password: string }) {
    return this.appService.login(body.email, body.password);
  }
}