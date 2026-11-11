import { Controller, Get, Post, Body, Query, Res, HttpStatus } from '@nestjs/common';
import { AppService, Message } from './app.service';
import { Response } from 'express';

@Controller('messages')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async getMessages(
    @Query('limit') limit: string,
    @Query('offset') offset: string,
    @Query('sort') sort: string,
    @Res() res: Response,
  ) {
    const lim = parseInt(limit || '10', 10);
    const off = parseInt(offset || '0', 10);
    const srt = sort || 'DESC';
    
    const html = await this.appService.getMessagesHtml(lim, off, srt);
    res.setHeader('Content-Type', 'text/html');
    return res.status(HttpStatus.OK).send(html);
  }

  @Post()
  async postMessage(@Body() message: Message, @Res() res: Response) {
    if (!message.username || !message.content) {
      return res.status(HttpStatus.BAD_REQUEST).send('Invalid input');
    }
    await this.appService.createMessage(message);
    return res.status(HttpStatus.OK).send();
  }
}