import { Controller, Post, Body, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';
import { Stream } from 'stream';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('download')
  async downloadSong(
    @Body('filename') filename: string,
    @Res() res: Response,
  ) {
    try {
      const stream: Stream = await this.appService.getSongStream(filename);
      
      // Set headers according to OpenAPI spec (audio/mpeg)
      res.set({
        'Content-Type': 'audio/mpeg',
        'Content-Disposition': `attachment; filename="${filename}"`,
      });

      stream.pipe(res);
    } catch (error) {
      // The service throws NestJS HTTP exceptions which are handled by the global filter,
      // but since we are using @Res(), we must send the response manually.
      const status = error.status || HttpStatus.INTERNAL_SERVER_ERROR;
      res.status(status).json({
        statusCode: status,
        message: error.message || 'Internal Server Error',
      });
    }
  }
}