import { Controller, Post, Body, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';
import { Stream } from 'stream';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('download')
  async downloadSong(
    @Body() body: { filename: string },
    @Res() res: Response,
  ) {
    const stream = await this.appService.getSongStream(body?.filename);
    
    // Set the content type to audio/mpeg as per OpenAPI spec
    res.setHeader('Content-Type', 'audio/mpeg');
    res.status(HttpStatus.OK);

    // Pipe the file stream directly to the express response
    stream.pipe(res);
  }
}