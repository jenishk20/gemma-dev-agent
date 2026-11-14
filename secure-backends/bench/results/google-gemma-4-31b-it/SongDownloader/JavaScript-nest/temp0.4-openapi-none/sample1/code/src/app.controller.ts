import { Controller, Post, Body, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';
import { Stream } from 'stream';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('download')
  async downloadSong(@Body() body: { filename: string }, @Res() res: Response) {
    try {
      const songStream: Stream = await this.appService.getSongStream(body.filename);
      
      // Set headers according to OpenAPI spec
      res.setHeader('Content-Type', 'audio/mpeg');
      res.status(HttpStatus.OK);
      
      // Pipe the file stream directly to the express response
      songStream.pipe(res);
    } catch (error) {
      // The service throws Nest HTTPExceptions which are handled by the global filter,
      // but since we use @Res(), we must handle the response manually.
      const status = error.getStatus ? error.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR;
      const message = error.message || 'Internal Server Error';
      res.status(status).json({ message });
    }
  }
}