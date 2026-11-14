import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  HttpCode, 
  HttpStatus, 
  BadRequestException, 
  Header 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('convert')
  @UseInterceptors(FileInterceptor('file'))
  @HttpCode(HttpStatus.OK)
  @Header('Content-Type', 'text/plain')
  async convertPdf(@UploadedFile() file: Express.Multer.File) {
    if (!file) {
      throw new BadRequestException('No file uploaded');
    }

    if (file.mimetype !== 'application/pdf') {
      throw new BadRequestException('Uploaded file must be a PDF');
    }

    return await this.appService.convertPdfToText(file.buffer);
  }
}