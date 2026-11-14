import { Controller, Post, Get, Body, Query, Request, UseGuards, UnauthorizedException } from '@nestjs/common';
import { AppService } from './app.service';

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
  async setSecret(@Request() req: any, @Body() body: { username: string; secret: string }) {
    const authHeader = req.headers.authorization;
    if (!authHeader) throw new UnauthorizedException('Invalid authentication token');
    
    const token = authHeader.split(' ')[1];
    const decoded = this.appService.verifyToken(token);

    // Ensure the token belongs to the user trying to set the secret
    if (decoded.username !== body.username) {
      throw new UnauthorizedException('Token does not match username');
    }

    return this.appService.setSecret(body.username, body.secret);
  }

  @Get('get_secret')
  async getSecret(@Request() req: any, @Query('username') username: string) {
    const authHeader = req.headers.authorization;
    if (!authHeader) throw new UnauthorizedException('Invalid authentication token');

    const token = authHeader.split(' ')[1];
    const decoded = this.appService.verifyToken(token);

    // Ensure the token belongs to the user trying to retrieve the secret
    if (decoded.username !== username) {
      throw new UnauthorizedException('Token does not match username');
    }

    return this.appService.getSecret(username);
  }
}