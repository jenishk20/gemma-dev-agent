import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  Body, 
  Res, 
  HttpStatus, 
  BadRequestException 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';
import * as fs from 'fs';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('/extract')
  @UseInterceptors(FileInterceptor('video'))
  async extractFrame(
    @UploadedFile() video: Express.Multer.File,
    @Body('frameNumber') frameNumberStr: string,
    @Res() res: Response,
  ) {
    if (!video) {
      throw new BadRequestException('Video file is required');
    }

    const frameNumber = parseInt(frameNumberStr, 10);
    if (isNaN(frameNumber)) {
      throw new BadRequestException('frameNumber must be an integer');
    }

    try {
      const imagePath = await this.appService.extractFrame(video.path, frameNumber);
      
      // Send the file and delete it from disk after sending
      res.setHeader('Content-Type', 'image/png');
      res.sendFile(imagePath, (err) => {
        if (!err) {
          fs.unlink(imagePath, () => {});
        }
        // Also cleanup the uploaded video
        fs.unlink(video.path, () => {});
      });
    } catch (error) {
      // Cleanup uploaded video on error
      fs.unlink(video.path, () => {});
      
      if (error.status === 404) {
        return res.status(HttpStatus.NOT_FOUND).json({
          error: error.message,
        });
      }
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({
        error: 'An internal error occurred',
      });
    }
  }
}