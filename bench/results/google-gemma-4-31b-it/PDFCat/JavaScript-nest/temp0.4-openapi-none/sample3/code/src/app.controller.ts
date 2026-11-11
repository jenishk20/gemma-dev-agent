import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFiles, 
  Res, 
  BadRequestException, 
  InternalServerErrorException 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';
import * as fs from 'fs';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('concatenate')
  @UseInterceptors(FileInterceptor('files'))
  async concatenate(
    @UploadedFiles() files: Express.Multer.File[],
    @Res() res: Response,
  ) {
    // NestJS FileInterceptor with 'files' array puts files in an array or a single file
    // We normalize it to an array
    const filesArray = Array.isArray(files) ? files : (files ? [files] : []);

    try {
      const resultPath = await this.appService.concatenatePdfs(filesArray);
      
      // Stream the resulting PDF back to the client
      const fileStream = fs.createReadStream(resultPath);
      
      res.setHeader('Content-Type', 'application/pdf');
      
      fileStream.on('end', async () => {
        await this.appService.cleanup(resultPath);
      });

      fileStream.pipe(res);
    } catch (error) {
      if (error instanceof BadRequestException) {
        return res.status(400).json({ error: error.message });
      }
      return res.status(500).json({ error: 'An error occurred while processing the files.' });
    }
  }
}