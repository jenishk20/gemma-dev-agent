import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFiles, 
  Body, 
  Res, 
  HttpStatus 
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('create-gif')
  @UseInterceptors(FilesInterceptor('images'))
  async createGif(
    @UploadedFiles() files: Express.Multer.File[],
    @Body('targetSize') targetSize: string,
    @Body('delay') delayStr: string,
    @Body('appendReverted') appendRevertedStr: string,
    @Res() res: Response,
  ) {
    const delay = delayStr ? parseInt(delayStr, 10) : 10;
    const appendReverted = appendRevertedStr === 'true';

    if (!targetSize) {
      return res.status(HttpStatus.BAD_REQUEST).json({ error: 'targetSize is required' });
    }

    try {
      const gifBuffer = await this.appService.createGif(files, targetSize, delay, appendReverted);
      
      res.set({
        'Content-Type': 'image/gif',
        'Content-Length': gifBuffer.length,
      });
      
      return res.status(HttpStatus.OK).send(gifBuffer);
    } catch (error) {
      if (error.status) {
        return res.status(error.status).json({ error: error.message });
      }
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({ error: 'Internal Server Error' });
    }
  }
}