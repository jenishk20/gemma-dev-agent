import { Controller, Post, Get, Body, Query, Req, UnauthorizedException } from '@nestjs/common';
import { AppService } from './app.service';
import { Request } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('register')
  async register(@Body() body: { email: string; username: string; password: string }) {
    return this.appService.register(body.email, body.username, body.password);
  }

  @Post('login')
  async login(@Body() body: { email: string; password: string }) {
    return this.appService.login(body.email, body.password);
  }

  @Post('set_secret')
  async setSecret(@Body() body: { username: string; secret: string }, @Req() req: Request) {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new UnauthorizedException('Invalid authentication token');
    }
    const token = authHeader.split(' ')[1];
    return this.appService.setSecret(body.username, body.secret, token);
  }

  @Get('get_secret')
  async getSecret(@Query('username') username: string, @Req() req: Request) {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new UnauthorizedException('Invalid authentication token');
    }
    const token = authHeader.split(' ')[1];
    return this.appService.getSecret(username, token);
  }
}