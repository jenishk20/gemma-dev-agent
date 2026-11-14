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
import { AppService } from './app.service';
import { Response } from 'express';
import * as fs from 'fs';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('extract')
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
      throw new BadRequestException('frameNumber must be a valid integer');
    }

    try {
      const imagePath = await this.appService.extractFrame(video, frameNumber);
      
      // Stream the file back to the user
      const fileStream = fs.createReadStream(imagePath);
      
      res.setHeader('Content-Type', 'image/png');
      
      fileStream.pipe(res);

      // Cleanup after the response is sent
      res.on('finish', async () => {
        await this.appService.cleanup(imagePath);
      });

    } catch (error) {
      // Let the service's NotFoundException propagate or handle it
      throw error;
    }
  }
}