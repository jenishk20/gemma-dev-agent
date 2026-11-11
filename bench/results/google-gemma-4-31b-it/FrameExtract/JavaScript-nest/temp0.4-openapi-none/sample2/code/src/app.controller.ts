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

  @Post('/extract')
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
      throw new BadRequestException('Valid frameNumber is required');
    }

    try {
      const imagePath = await this.appService.extractFrame(video, frameNumber);
      
      // Stream the file to the response
      const fileStream = fs.createReadStream(imagePath);
      
      res.setHeader('Content-Type', 'image/png');
      fileStream.pipe(res);

      // Delete the temporary image after the response is finished
      res.on('finish', async () => {
        await this.appService.deleteTempFile(imagePath);
      });
    } catch (error) {
      // If it's a NestJS HTTP exception, rethrow it, otherwise send 404 as per schema
      if (error.status) {
        return res.status(error.status).json({ error: error.message });
      }
      return res.status(404).json({ error: `Frame at index ${frameNumber} could not be found.` });
    }
  }
}