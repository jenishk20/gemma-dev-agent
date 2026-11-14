import { Controller, Get, Post, Put, Param, Body, Res } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('entries')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async findAll(@Res() res: Response) {
    const html = await this.appService.getAllEntries();
    res.set('Content-Type', 'text/html');
    return res.send(html);
  }

  @Post()
  async create(@Body() createDto: any) {
    return this.appService.createEntry(createDto);
  }

  @Get(':entryId')
  async findOne(@Param('entryId') entryId: string, @Res() res: Response) {
    const html = await this.appService.getEntry(entryId);
    res.set('Content-Type', 'text/html');
    return res.send(html);
  }

  @Put(':entryId')
  async update(@Param('entryId') entryId: string, @Body() updateDto: any) {
    return this.appService.updateEntry(entryId, updateDto);
  }

  @Get(':entryId/edits')
  async getEdits(@Param('entryId') entryId: string, @Res() res: Response) {
    const html = await this.appService.getEdits(entryId);
    res.set('Content-Type', 'text/html');
    return res.send(html);
  }
}