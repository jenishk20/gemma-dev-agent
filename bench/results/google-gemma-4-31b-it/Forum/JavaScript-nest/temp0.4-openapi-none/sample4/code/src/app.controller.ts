import { Controller, Get, Post, Body, Query, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('messages')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post()
  async postMessage(@Body() body: { username: string; content: string }) {
    if (!body.username || !body.content) {
      // This will be handled by the 400 response requirement
      throw new Error('Invalid input');
    }
    await this.appService.createMessage(body.username, body.content);
    return { message: 'Successful operation' };
  }

  @Get()
  async getMessages(
    @Query('limit') limit: string,
    @Query('offset') offset: string,
    @Query('sort') sort: string,
    @Res() res: Response,
  ) {
    const limitNum = parseInt(limit || '10', 10);
    const offsetNum = parseInt(offset || '0', 10);
    const sortDir = (sort?.toUpperCase() === 'ASC') ? 'ASC' : 'DESC';

    const messages = await this.appService.getMessages(limitNum, offsetNum, sortDir);

    let html = `
      <!DOCTYPE html>
      <html>
        <head><title>MyForum</title></head>
        <body style="font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px;">
          <h1>MyForum Messages</h1>
          <hr/>
          <div style="margin-bottom: 20px;">
            <form action="/messages" method="POST" style="display: flex; flex-direction: column; gap: 10px; width: 300px;">
              <input name="username" placeholder="Username" required />
              <textarea name="content" placeholder="Message" required></textarea>
              <button type="submit">Post Message</button>
            </form>
          </div>
          <hr/>
          <div style="display: flex; flex-direction: column; gap: 15px;">
    `;

    messages.forEach(msg => {
      html += `
        <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px;">
          <strong>${this.escapeHtml(msg.username)}</strong> 
          <small style="color: gray;">${msg.created_at}</small>
          <p>${this.escapeHtml(msg.content)}</p>
        </div>
      `;
    });

    html += `
          </div>
        </body>
      </html>
    `;

    res.set('Content-Type', 'text/html');
    res.status(HttpStatus.OK).send(html);
  }

  private escapeHtml(unsafe: string): string {
    return unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}