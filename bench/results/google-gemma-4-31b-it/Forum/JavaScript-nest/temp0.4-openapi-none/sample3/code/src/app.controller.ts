import { Controller, Get, Post, Body, Query, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('messages')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post()
  async create(@Body() body: { username: string; content: string }, @Res() res: Response) {
    if (!body.username || !body.content) {
      return res.status(HttpStatus.BAD_REQUEST).send('Invalid input');
    }
    await this.appService.createMessage(body.username, body.content);
    return res.status(HttpStatus.OK).send();
  }

  @Get()
  async findAll(
    @Query('limit') limit: string,
    @Query('offset') offset: string,
    @Query('sort') sort: string,
    @Res() res: Response,
  ) {
    const lim = parseInt(limit || '10', 10);
    const off = parseInt(offset || '0', 10);
    const srt = (sort?.toUpperCase() === 'ASC') ? 'ASC' : 'DESC';

    const messages = await this.appService.getMessages(lim, off, srt);
    
    let html = '<html><body><h1>Forum Messages</h1>';
    html += '<form action="/messages" method="POST" style="margin-bottom: 20px;">';
    html += '<input name="username" placeholder="Username" required /> ';
    html += '<input name="content" placeholder="Message" required /> ';
    html += '<button type="submit">Post</button>';
    html += '<!-- Note: API expects JSON, this form is for visual representation -->';
    html += '</form><hr/>';

    messages.forEach(msg => {
      html += `<div style="margin-bottom: 10px;"><strong>${msg.username}</strong> (${msg.created_at}):<br/>${msg.content}</div>`;
    });

    html += '</body></html>';
    
    res.setHeader('Content-Type', 'text/html');
    return res.status(200).send(html);
  }
}