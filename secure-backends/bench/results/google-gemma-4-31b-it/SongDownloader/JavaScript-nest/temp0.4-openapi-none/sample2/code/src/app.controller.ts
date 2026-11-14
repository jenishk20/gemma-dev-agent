import { Controller, Post, Body, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('download')
  async downloadSong(@Body() body: { filename: string }, @Res() res: Response) {
    try {
      const stream = await this.appService.getSongStream(body.filename);
      
      // Set the content type to audio/mpeg as per OpenAPI spec
      res.setHeader('Content-Type', 'audio/mpeg');
      res.setHeader('Content-Disposition', `attachment; filename="${body.filename}"`);
      
      // Pipe the file stream directly to the express response
      stream.pipe(res);
    } catch (error) {
      // The service throws NestJS HTTP exceptions which are handled by the global filter,
      // but since we use @Res(), we must handle the response manually.
      const status = error.status || HttpStatus.INTERNAL_SERVER_ERROR;
      res.status(status).json({
        statusCode: status,
        message: error.message || 'Internal Server Error',
      });
    }
  }
}