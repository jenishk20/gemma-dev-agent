import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('heartbeat')
  async heartbeat(@Body() body: { serviceId?: string; token?: string }) {
    if (!body.serviceId || !body.token) {
      throw new BadRequestException('serviceId and token are required');
    }
    return await this.appService.registerHeartbeat(body.serviceId, body.token);
  }

  @Post('services')
  async getServices(@Body() body: { token?: string }) {
    if (!body.token) {
      throw new BadRequestException('token is required');
    }
    return await this.appService.getServicesByToken(body.token);
  }
}