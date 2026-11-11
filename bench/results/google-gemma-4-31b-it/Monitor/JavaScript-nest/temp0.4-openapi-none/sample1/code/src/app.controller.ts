import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

interface MonitorRequest {
  filter_flags?: string;
  command_regex: string;
}

@Controller('monitor')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('commands')
  async retrieveProcesses(@Body() body: MonitorRequest) {
    if (!body.command_regex) {
      throw new BadRequestException('command_regex is required');
    }

    return await this.appService.getProcesses(
      body.filter_flags || '', 
      body.command_regex
    );
  }
}