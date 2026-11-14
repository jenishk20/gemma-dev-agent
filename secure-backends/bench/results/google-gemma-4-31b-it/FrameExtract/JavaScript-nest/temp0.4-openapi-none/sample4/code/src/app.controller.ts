import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  Body, 
  Res, 
  HttpStatus, 
  NotFoundException 
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
      return res.status(HttpStatus.BAD_REQUEST).json({ error: 'Video file is required' });
    }

    const frameNumber = parseInt(frameNumberStr, 10);
    if (isNaN(frameNumber)) {
      return res.status(HttpStatus.BAD_REQUEST).json({ error: 'Valid frameNumber is required' });
    }

    try {
      const imagePath = await this.appService.extractFrame(video.path, frameNumber);
      
      // Send the image file and then delete the temporary files
      res.setHeader('Content-Type', 'image/png');
      const fileBuffer = fs.readFileSync(imagePath);
      
      // Clean up both the uploaded video and the extracted frame
      await this.appService.deleteFile(video.path);
      await this.appService.deleteFile(imagePath);

      return res.send(fileBuffer);
    } catch (error) {
      // Cleanup video if extraction failed
      await this.appService.deleteFile(video.path);
      
      if (error instanceof NotFoundException) {
        return res.status(HttpStatus.NOT_FOUND).json({ 
          error: error.message 
        });
      }
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({ 
        error: 'An internal error occurred during frame extraction' 
      });
    }
  }
}