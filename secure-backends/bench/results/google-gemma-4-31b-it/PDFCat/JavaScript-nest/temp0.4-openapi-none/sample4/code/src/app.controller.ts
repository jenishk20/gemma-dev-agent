import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFiles, 
  Res, 
  BadRequestException 
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('concatenate')
  @UseInterceptors(FilesInterceptor('files'))
  async concatenate(
    @UploadedFiles() files: Express.Multer.File[],
    @Res() res: Response,
  ) {
    if (!files || files.length === 0) {
      throw new BadRequestException('Invalid input or missing files.');
    }
    
    await this.appService.concatenatePdfs(files, res);
  }
}