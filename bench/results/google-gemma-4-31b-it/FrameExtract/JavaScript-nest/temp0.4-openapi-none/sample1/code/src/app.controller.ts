import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  Body, 
  Res, 
  BadRequestException 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { Response } from 'express';
import { AppService } from './app.service';
import * as fs from 'fs';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('extract')
  @UseInterceptors(FileInterceptor('video'))
  async extractFrame(
    @UploadedFile() video: Express.Multer.File,
    @Body('frameNumber') frameNumberStr: string,
    @Body('videoFileName') videoFileName: string,
    @Res() res: Response,
  ) {
    if (!video) {
      throw new BadRequestException('Video file is required');
    }

    const frameNumber = parseInt(frameNumberStr, 10);
    if (isNaN(frameNumber)) {
      throw new BadRequestException('frameNumber must be a valid integer');
    }

    let outputPath = '';
    try {
      outputPath = await this.appService.extractFrame(video, frameNumber);
      
      const imageBuffer = fs.readFileSync(outputPath);
      res.set('Content-Type', 'image/png');
      res.send(imageBuffer);
    } catch (error) {
      throw error;
    } finally {
      if (outputPath) {
        this.appService.cleanup(outputPath);
      }
    }
  }
}