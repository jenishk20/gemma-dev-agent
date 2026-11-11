import { 
  Controller, 
  Post, 
  Get, 
  Param, 
  UseInterceptors, 
  UploadedFile, 
  Res, 
  HttpStatus 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';
import * as fs from 'fs';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('upload')
  @UseInterceptors(FileInterceptor('file'))
  async uploadImage(@UploadedFile() file: Express.Multer.File, @Res() res: Response) {
    if (!file) {
      return res.status(HttpStatus.BAD_REQUEST).json({ error: 'File is required' });
    }

    try {
      const id = await this.appService.saveImage(file);
      return res.status(HttpStatus.OK).json({ id });
    } catch (error) {
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({ error: 'Internal server error' });
    }
  }

  @Get('images/:imageId')
  async serveImage(@Param('imageId') imageId: string, @Res() res: Response) {
    try {
      const { path, mimetype } = this.appService.getImagePath(imageId);
      
      // Set content type to ensure browser renders it instead of downloading
      res.setHeader('Content-Type', mimetype);
      res.setHeader('Content-Disposition', 'inline');
      
      const stream = fs.createReadStream(path);
      stream.pipe(res);
    } catch (error) {
      if (error.status === 404) {
        return res.status(HttpStatus.NOT_FOUND).json({ error: 'Image not found' });
      }
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({ error: 'Internal server error' });
    }
  }
}