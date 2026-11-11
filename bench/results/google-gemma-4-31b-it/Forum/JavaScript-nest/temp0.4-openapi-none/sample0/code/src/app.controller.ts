import { 
  Controller, 
  Get, 
  Post, 
  Body, 
  Query, 
  Res, 
  HttpStatus, 
  BadRequestException 
} from '@nestjs/common';
import { AppService } from './app.service';
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
    const parsedLimit = parseInt(limit || '10', 10);
    const parsedOffset = parseInt(offset || '0', 10);
    const parsedSort = (sort?.toUpperCase() === 'ASC' ? 'ASC' : 'DESC') as 'ASC' | 'DESC';

    const html = await this.appService.getMessages(parsedLimit, parsedOffset, parsedSort);
    
    res.setHeader('Content-Type', 'text/html');
    return res.status(HttpStatus.OK).send(html);
  }

  @Post()
  async postMessage(@Body() body: { username?: string; content?: string }, @Res() res: Response) {
    if (!body.username || !body.content) {
      throw new BadRequestException('Username and content are required');
    }
    
    await this.appService.createMessage(body.username, body.content);
    return res.status(HttpStatus.OK).send();
  }
}