import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
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
  @UseInterceptors(FileInterceptor('file'))
  async convert(@UploadedFile() file: Express.Multer.File, @Res() res: Response) {
    try {
      const text = await this.appService.convertPdfToText(file);
      
      // Set content type to text/plain as per OpenAPI schema
      res.setHeader('Content-Type', 'text/plain');
      return res.status(HttpStatus.OK).send(text);
    } catch (error) {
      // The service throws Nest HTTPExceptions which are handled by the global filter,
      // but since we are using @Res(), we must handle the response manually.
      const status = error.status || HttpStatus.INTERNAL_SERVER_ERROR;
      const message = error.message || 'Internal Server Error';
      
      return res.status(status).json({
        error: message
      });
    }
  }
}