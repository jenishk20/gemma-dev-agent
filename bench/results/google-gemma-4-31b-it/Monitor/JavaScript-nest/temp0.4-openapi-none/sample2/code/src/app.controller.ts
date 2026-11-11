import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

interface MonitorRequest {
  filter_flags?: string;
  command_regex: string;
}

@Controller('monitor')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('commands')
  @HttpCode(HttpStatus.OK)
  async retrieveProcesses(@Body() body: MonitorRequest) {
    const filterFlags = body.filter_flags || 'aux';
    const commandRegex = body.command_regex;
    return this.appService.getProcesses(filterFlags, commandRegex);
  }
}