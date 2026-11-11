import { Controller, Post, UseInterceptors, UploadedFile, BadRequestException, Header } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('convert')
  @UseInterceptors(FileInterceptor('file'))
  @Header('Content-Type', 'text/plain')
  async convert(@UploadedFile() file: Express.Multer.File) {
    if (!file) {
      throw new BadRequestException('No file uploaded');
    }
    
    return await this.appService.convertZipToText(file.buffer);
  }
}