import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
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
  @UseInterceptors(FileInterceptor('file'))
  async convert(@UploadedFile() file: Express.Multer.File, @Res() res: Response) {
    if (!file) {
      throw new BadRequestException('File is required');
    }

    try {
      const result = await this.appService.convertZipToText(file.buffer);
      
      // Set content type to text/plain as per OpenAPI spec
      res.setHeader('Content-Type', 'text/plain');
      return res.status(200).send(result);
    } catch (e) {
      if (e instanceof BadRequestException) {
        throw e;
      }
      throw new BadRequestException('An error occurred during conversion');
    }
  }
}