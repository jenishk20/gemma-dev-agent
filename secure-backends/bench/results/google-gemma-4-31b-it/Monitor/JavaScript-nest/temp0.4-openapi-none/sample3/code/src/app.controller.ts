import { Controller, Post, Body } from '@nestjs/common';
import { AppService } from './app.service';

interface MonitorRequest {
  filter_flags?: string;
  command_regex: string;
}

interface ProcessInfo {
  processId: number;
  processString: string;
}

@Controller('monitor')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('commands')
  async retrieveProcesses(@Body() body: MonitorRequest): Promise<ProcessInfo[]> {
    if (!body.command_regex) {
      throw new Error('command_regex is required');
    }
    return this.appService.getProcesses(body.filter_flags, body.command_regex);
  }
}