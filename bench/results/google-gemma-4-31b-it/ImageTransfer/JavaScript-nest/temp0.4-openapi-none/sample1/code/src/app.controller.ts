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
import { Response } from 'express';
import { AppService } from './app.service';

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
      return res.status(HttpStatus.BAD_REQUEST).json({ error: 'File is required' });
    }

    try {
      const id = await this.appService.saveImage(file);
      return res.status(HttpStatus.OK).json({ id });
    } catch (e) {
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({ error: 'Internal server error' });
    }
  }

  @Get('images/:imageId')
  async shareImage(
    @Param('imageId') imageId: string, 
    @Res() res: Response
  ) {
    try {
      const { buffer, mimetype } = await this.appService.getImage(imageId);
      
      // Setting Content-Type allows the browser to render the image
      // Not setting Content-Disposition: attachment ensures it doesn't force download
      res.setHeader('Content-Type', mimetype);
      res.setHeader('Content-Length', buffer.length);
      
      return res.status(HttpStatus.OK).send(buffer);
    } catch (e) {
      if (e.status === 404) {
        return res.status(HttpStatus.NOT_FOUND).json({ error: 'Image not found' });
      }
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).json({ error: 'Internal server error' });
    }
  }
}