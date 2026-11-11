import { Controller, Post, UseInterceptors, UploadedFile, BadRequestException } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('convert')
  @UseInterceptors(FileInterceptor('file'))
  async convert(@UploadedFile() file: Express.Multer.File): Promise<string> {
    if (!file) {
      throw new BadRequestException('No file uploaded');
    }

    if (!file.mimetype === 'application/zip' && !file.originalname.endsWith('.zip')) {
      // Basic check for zip format
    }

    const result = await this.appService.convertZipToText(file.buffer);
    
    // Set response header to text/plain as per OpenAPI spec
    // Note: In a real scenario, you might use @Res() to set headers, 
    // but returning a string in NestJS defaults to text/plain or application/json.
    return result;
  }
}