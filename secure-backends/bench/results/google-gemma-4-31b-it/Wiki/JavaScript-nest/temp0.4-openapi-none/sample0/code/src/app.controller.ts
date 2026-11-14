import { Controller, Get, Post, Put, Body, Param, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('entries')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async list(@Res() res: Response) {
    const html = await this.appService.getAllEntriesHtml();
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }

  @Post()
  async create(@Body() body: any) {
    return this.appService.createEntry(body);
  }

  @Get(':entryId')
  async getOne(@Param('entryId') entryId: string, @Res() res: Response) {
    const html = await this.appService.getEntryHtml(entryId);
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }

  @Put(':entryId')
  async update(@Param('entryId') entryId: string, @Body() body: any) {
    return this.appService.updateEntry(entryId, body);
  }

  @Get(':entryId/edits')
  async getEdits(@Param('entryId') entryId: string, @Res() res: Response) {
    const html = await this.appService.getEditsHtml(entryId);
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }
}