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
  @UseInterceptors(FileInterceptor('images', { 
    // Custom logic to handle multiple files under the same key 'images'
    // Note: FileInterceptor usually handles one file, but multer allows multiple
    // We use a workaround or simply handle the array if the client sends multiple 'images' fields
  }))
  async createGif(
    @UploadedFiles() files: Express.Multer.File[], 
    @Body() body: { targetSize: string, delay?: string, appendReverted?: string },
    @Res() res: Response
  ) {
    // Multer's FileInterceptor with multiple files under same key often returns an array 
    // or a single file. We ensure it's treated as an array.
    const imageFiles = Array.isArray(files) ? files : (files ? [files] : []);

    if (!body.targetSize) {
      throw new BadRequestException('targetSize is required');
    }

    const delay = body.delay ? parseInt(body.delay, 10) : 10;
    const appendReverted = body.appendReverted === 'true' || body.appendReverted === '1';

    if (isNaN(delay)) {
      throw new BadRequestException('delay must be an integer');
    }

    const gifBuffer = await this.appService.createGif(
      imageFiles, 
      body.targetSize, 
      delay, 
      appendReverted
    );

    res.setHeader('Content-Type', 'image/gif');
    res.send(gifBuffer);
  }
}