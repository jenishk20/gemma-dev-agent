import { Controller, Post, Body } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('invite_user')
  async inviteUser(@Body() body: { email: string }) {
    if (!body.email) {
      return { message: 'Email is required' };
    }
    return await this.appService.inviteUser(body.email);
  }

  @Post('create_user')
  async createUser(@Body() body: { invite_id: string, user_name: string, password: string }) {
    const { invite_id, user_name, password } = body;
    if (!invite_id || !user_name || !password) {
      return { message: 'Missing required fields: invite_id, user_name, and password are required.' };
    }
    return await this.appService.createUser(invite_id, user_name, password);
  }
}