import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  HttpCode, 
  Res, 
  HttpStatus 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('convert')
  @HttpCode(HttpStatus.OK)
  @UseInterceptors(FileInterceptor('file'))
  async convert(
    @UploadedFile() file: Express.Multer.File, 
    @Res() res: Response
  ) {
    if (!file) {
      return res.status(400).send('Missing file');
    }

    try {
      const text = await this.appService.convertPdfToText(file);
      
      // Set content-type to text/plain as per OpenAPI schema
      res.setHeader('Content-Type', 'text/plain');
      return res.status(200).send(text);
    } catch (error) {
      // Let NestJS exception filters handle the response or send manually
      return res.status(error.status || 500).json({
        error: error.message || 'Internal Server Error'
      });
    }
  }
}