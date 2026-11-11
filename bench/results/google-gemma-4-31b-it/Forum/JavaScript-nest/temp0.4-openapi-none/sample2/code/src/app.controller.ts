import { Controller, Get, Post, Body, Query, HttpCode, Header, Res } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('messages')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  @Header('Content-Type', 'text/html')
  async getMessages(
    @Query('limit') limit: string = '10',
    @Query('offset') offset: string = '0',
    @Query('sort') sort: string = 'DESC',
  ): Promise<string> {
    return this.appService.getMessagesHtml(
      parseInt(limit),
      parseInt(offset),
      sort,
    );
  }

  @Post()
  @HttpCode(200)
  async postMessage(@Body() body: { username: string; content: string }) {
    if (!body.username || !body.content) {
      throw new Error('Invalid input');
    }
    await this.appService.createMessage(body.username, body.content);
    return { status: 'Successful operation' };
  }
}