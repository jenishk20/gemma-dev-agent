import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('invite_user')
  @HttpCode(HttpStatus.OK)
  async inviteUser(@Body('email') email: string) {
    return this.appService.inviteUser(email);
  }

  @Post('create_user')
  @HttpCode(HttpStatus.OK)
  async createUser(
    @Body('invite_id') inviteId: string,
    @Body('user_name') userName: string,
    @Body('password') password: string,
  ) {
    return this.appService.createUser(inviteId, userName, password);
  }
}