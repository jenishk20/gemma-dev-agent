import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFiles, 
  Res, 
  BadRequestException, 
  InternalServerErrorException 
} from '@nestjs/common';
import { FileInterceptor, FilesInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';
import * as fs from 'fs';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('concatenate')
  @UseInterceptors(FilesInterceptor('files'))
  async concatenate(
    @UploadedFiles() files: Express.Multer.File[], 
    @Res() res: Response
  ) {
    if (!files || files.length === 0) {
      return res.status(400).json({ error: 'Invalid input or missing files.' });
    }

    let resultPath: string | null = null;
    try {
      resultPath = await this.appService.concatenatePdfs(files);
      
      const fileBuffer = fs.readFileSync(resultPath);
      
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', 'attachment; filename="concatenated.pdf"');
      res.status(200).send(fileBuffer);

      // Cleanup temp files after sending response
      await this.appService.cleanup(resultPath);
    } catch (error) {
      if (resultPath) await this.appService.cleanup(resultPath);
      
      if (error instanceof BadRequestException) {
        return res.status(400).json({ error: error.message });
      }
      return res.status(500).json({ error: 'An error occurred while processing the files.' });
    }
  }
}