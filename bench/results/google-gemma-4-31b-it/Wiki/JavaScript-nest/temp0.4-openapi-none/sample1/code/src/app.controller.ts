import { Controller, Get, Post, Put, Param, Body, Header, Res } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('entries')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async listEntries(@Res() res: Response) {
    const html = await this.appService.getAllEntriesHtml();
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }

  @Post()
  async create(@Body() body: { title: string, content: string, createdBy: string }) {
    return this.appService.createEntry(body);
  }

  @Get(':entryId')
  async getEntry(@Param('entryId') id: string, @Res() res: Response) {
    const html = await this.appService.getEntryHtml(id);
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }

  @Put(':entryId')
  async update(@Param('entryId') id: string, @Body() body: { content: string, modifiedBy: string, summary: string }) {
    return this.appService.updateEntry(id, body);
  }

  @Get(':entryId/edits')
  async getEdits(@Param('entryId') id: string, @Res() res: Response) {
    const html = await this.appService.getEditsHtml(id);
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }
}