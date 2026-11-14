import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  HttpCode, 
  Res, 
  BadRequestException 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('convert')
  @HttpCode(200)
  @UseInterceptors(FileInterceptor('file'))
  async convert(
    @UploadedFile() file: Express.Multer.File, 
    @Res() res: Response
  ) {
    if (!file) {
      throw new BadRequestException('File is required');
    }

    try {
      const result = await this.appService.convertZipToText(file.buffer);
      res.setHeader('Content-Type', 'text/plain');
      return res.send(result);
    } catch (e) {
      throw e;
    }
  }
}