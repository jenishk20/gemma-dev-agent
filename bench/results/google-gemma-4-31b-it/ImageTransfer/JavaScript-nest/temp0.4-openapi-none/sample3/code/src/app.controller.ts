import { 
  Controller, 
  Post, 
  Get, 
  Param, 
  UseInterceptors, 
  UploadedFile, 
  Res, 
  BadRequestException, 
  InternalServerErrorException 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { Response } from 'express';
import { AppService } from './app.service';
import { NotFoundException } from '@nestjs/common';

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
      throw new BadRequestException({ error: 'No file uploaded' });
    }

    try {
      const id = await this.appService.saveImage(file);
      return res.status(200).json({ id });
    } catch (error) {
      throw new InternalServerErrorException({ error: 'Internal server error during upload' });
    }
  }

  @Get('images/:imageId')
  async shareImage(
    @Param('imageId') imageId: string, 
    @Res() res: Response
  ) {
    try {
      const meta = this.appService.getImageMetadata(imageId);
      const stream = this.appService.getImageStream(meta.path);

      // Set content type to original mimetype so browser renders it
      res.setHeader('Content-Type', meta.mimetype);
      // Ensure it's viewed in browser, not downloaded
      res.setHeader('Content-Disposition', 'inline');

      stream.pipe(res);
    } catch (error) {
      if (error instanceof NotFoundException) {
        return res.status(404).json({ error: 'Image not found' });
      }
      return res.status(500).json({ error: 'Internal server error' });
    }
  }
}