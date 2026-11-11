import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFiles, 
  Res 
} from '@nestjs/common';
import { FilesInterceptor } from '@nestjs/platform-express';
import { Response } from 'express';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('concatenate')
  @UseInterceptors(FilesInterceptor('files'))
  async concatenate(
    @UploadedFiles() files: Express.Multer.File[], 
    @Res() res: Response
  ) {
    try {
      if (!files || files.length === 0) {
        return res.status(400).json({ error: 'Invalid input or missing files.' });
      }

      const pdfBuffer = await this.appService.concatenatePdfs(files);
      
      res.setHeader('Content-Type', 'application/pdf');
      res.send(pdfBuffer);
    } catch (error) {
      if (error.status === 400) {
        return res.status(400).json({ error: 'Invalid input or missing files.' });
      }
      return res.status(500).json({ error: 'An error occurred while processing the files.' });
    }
  }
}