import { Controller, Post, Body, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('download')
  async downloadSong(@Body() body: { filename: string }, @Res() res: Response) {
    const stream = await this.appService.getSongStream(body?.filename);
    
    res.set({
      'Content-Type': 'audio/mpeg',
      'Content-Disposition': `attachment; filename="${body.filename}"`,
    });

    stream.pipe(res);
  }
}