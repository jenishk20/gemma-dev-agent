import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  HttpCode, 
  Res 
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
  async convertPdf(
    @UploadedFile() file: Express.Multer.File, 
    @Res() res: Response
  ) {
    const text = await this.appService.convertPdfToText(file);
    
    // Set content type to text/plain as per OpenAPI spec
    res.setHeader('Content-Type', 'text/plain');
    return res.send(text);
  }
}