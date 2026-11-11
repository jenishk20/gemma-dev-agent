import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  Res, 
  BadRequestException, 
  HttpStatus 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('convert')
  @UseInterceptors(FileInterceptor('file'))
  async convert(@UploadedFile() file: Express.Multer.File, @Res() res: Response) {
    if (!file) {
      throw new BadRequestException('No file uploaded');
    }

    if (file.mimetype !== 'application/pdf') {
      throw new BadRequestException('Uploaded file must be a PDF');
    }

    try {
      const text = await this.appService.convertPdfToText(file.buffer);
      
      res.set('Content-Type', 'text/plain');
      return res.status(HttpStatus.OK).send(text);
    } catch (error) {
      if (error instanceof BadRequestException) {
        throw error;
      }
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({
        error: error.message || 'Internal Server Error'
      });
    }
  }
}