import { Controller, Post, Body, BadRequestException, InternalServerErrorException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('heartbeat')
  async heartbeat(@Body() body: { serviceId?: string; token?: string }) {
    if (!body.serviceId || !body.token) {
      throw new BadRequestException('Missing serviceId or token');
    }
    try {
      await this.appService.registerHeartbeat(body.serviceId, body.token);
      return { message: 'Heartbeat registered successfully' };
    } catch (error) {
      throw new InternalServerErrorException('Internal server error');
    }
  }

  @Post('services')
  async getServices(@Body() body: { token?: string }) {
    if (!body.token) {
      throw new BadRequestException('Missing token');
    }
    try {
      const services = await this.appService.getServicesByToken(body.token);
      return services;
    } catch (error) {
      throw new InternalServerErrorException('Internal server error');
    }
  }
}