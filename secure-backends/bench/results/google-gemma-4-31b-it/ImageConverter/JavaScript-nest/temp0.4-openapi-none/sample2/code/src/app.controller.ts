import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFiles, 
  Body, 
  Res, 
  BadRequestException 
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';
import * as fs from 'fs';

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
    if (!targetSize) {
      throw new BadRequestException('targetSize is required');
    }

    const delay = delayStr ? parseInt(delayStr, 10) : 10;
    const appendReverted = appendRevertedStr === 'true';

    if (isNaN(delay)) {
      throw new BadRequestException('delay must be a number');
    }

    const gifPath = await this.appService.createGif(files, targetSize, delay, appendReverted);
    
    try {
      const fileBuffer = fs.readFileSync(gifPath);
      res.setHeader('Content-Type', 'image/gif');
      res.send(fileBuffer);
    } finally {
      // Cleanup temp files after sending response
      await this.appService.cleanup(gifPath);
    }
  }
}