import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFiles, 
  Body, 
  Res, 
  BadRequestException 
} from '@nestjs/common';
import { FileInterceptor, FilesInterceptor } from '@nestjs/platform-express';
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
    if (!files || files.length === 0) {
      throw new BadRequestException('images field is required');
    }
    if (!targetSize) {
      throw new BadRequestException('targetSize is required');
    }

    const delay = delayStr ? parseInt(delayStr, 10) : 10;
    const appendReverted = appendRevertedStr === 'true';

    if (isNaN(delay)) {
      throw new BadRequestException('delay must be a number');
    }

    const gifBuffer = await this.appService.createGif(files, targetSize, delay, appendReverted);
    
    res.setHeader('Content-Type', 'image/gif');
    res.send(gifBuffer);
  }
}