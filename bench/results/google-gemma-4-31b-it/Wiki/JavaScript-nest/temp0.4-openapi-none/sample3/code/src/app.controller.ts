import { Controller, Get, Post, Put, Param, Body, HttpCode, Header, Req } from '@nestjs/common';
import { AppService } from './app.service';
import { Request } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('entries')
  @Header('Content-Type', 'text/html')
  async getEntries() {
    return this.appService.getAllEntriesHtml();
  }

  @Post('entries')
  @HttpCode(201)
  async createEntry(@Body() body: any) {
    // Handle both JSON and Form-urlencoded (for the HTML form)
    const data = {
      title: body.title,
      content: body.content,
      createdBy: body.createdBy,
    };
    return this.appService.createEntry(data);
  }

  @Get('entries/:entryId')
  @Header('Content-Type', 'text/html')
  async getEntry(@Param('entryId') entryId: string) {
    return this.appService.getEntryHtml(entryId);
  }

  @Put('entries/:entryId')
  async updateEntry(@Param('entryId') entryId: string, @Body() body: any) {
    return this.appService.updateEntry(entryId, body);
  }

  // Since HTML forms only support GET/POST, we map a POST to the PUT logic for the UI
  @Post('entries/:entryId')
  @Header('Content-Type', 'text/html')
  async updateEntryFromForm(@Param('entryId') entryId: string, @Body() body: any) {
    await this.appService.updateEntry(entryId, body);
    return `<html><body>Update successful. <a href="/entries/${entryId}">Go back</a></body></html>`;
  }

  @Get('entries/:entryId/edits')
  @Header('Content-Type', 'text/html')
  async getEdits(@Param('entryId') entryId: string) {
    return this.appService.getEditsHtml(entryId);
  }
}