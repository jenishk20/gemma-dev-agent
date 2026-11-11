import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFiles, 
  Body, 
  Res, 
  BadRequestException 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('create-gif')
  @UseInterceptors(FileInterceptor('images'))
  async createGif(
    @UploadedFiles() files: Express.Multer.File[],
    @Body() body: { targetSize?: string, delay?: string, appendReverted?: string },
    @Res() res: Response
  ) {
    // Multer handles multiple files under the same key as an array if configured, 
    // but FileInterceptor handles a single field. For multiple files in one field, 
    // we check if files is an array or a single object.
    const imageFiles = Array.isArray(files) ? files : (files ? [files] : []);

    const targetSize = body.targetSize;
    if (!targetSize) {
      throw new BadRequestException('targetSize is required');
    }

    const delay = body.delay ? parseInt(body.delay, 10) : 10;
    const appendReverted = body.appendReverted === 'true' || body.appendReverted === true;

    try {
      const gifBuffer = await this.appService.createGif(imageFiles, targetSize, delay, appendReverted);
      
      res.setHeader('Content-Type', 'image/gif');
      res.send(gifBuffer);
    } catch (error) {
      // Re-throw NestJS HTTP exceptions to let the global filter handle them
      throw error;
    }
  }
}