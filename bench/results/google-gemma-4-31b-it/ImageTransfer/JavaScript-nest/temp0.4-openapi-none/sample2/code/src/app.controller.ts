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
import { Stream } from 'stream';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('upload')
  @UseInterceptors(FileInterceptor('file'))
  async uploadImage(
    @UploadedFile() file: Express.Multer.File, 
    @Res() res: Response
  ) {
    if (!file) {
      return res.status(HttpStatus.BAD_REQUEST).json({ error: 'No file uploaded' });
    }
    try {
      const id = await this.appService.saveImage(file);
      return res.status(HttpStatus.OK).json({ id });
    } catch (e) {
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({ error: 'Internal server error' });
    }
  }

  @Get('images/:imageId')
  async serveImage(
    @Param('imageId') imageId: string, 
    @Res() res: Response
  ) {
    try {
      const meta = this.appService.getImageMetadata(imageId);
      const stream: Stream = this.appService.getImageStream(imageId);

      // Set content type to original mimetype to ensure browser renders it
      res.setHeader('Content-Type', meta.mimetype);
      // We do NOT set Content-Disposition to attachment, so it opens in browser
      
      stream.pipe(res);
    } catch (e) {
      if (e.status === 404) {
        return res.status(HttpStatus.NOT_FOUND).json({ error: 'Image not found' });
      }
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({ error: 'Internal server error' });
    }
  }
}