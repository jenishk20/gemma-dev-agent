import { 
  Controller, 
  Post, 
  Get, 
  UseInterceptors, 
  UploadedFile, 
  Param, 
  Res, 
  BadRequestException 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { Response } from 'express';
import { AppService } from './app.service';
import * as fs from 'fs';
import * as path from 'path';
import { diskStorage } from 'multer';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('upload')
  @UseInterceptors(FileInterceptor('file', {
    storage: diskStorage({
      destination: (req, file, cb) => {
        const uploadDir = path.join(process.cwd(), 'uploads');
        if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir);
        cb(null, uploadDir);
      },
      filename: (req, file, cb) => {
        cb(null, `${Date.now()}-${file.originalname}`);
      },
    }),
  }))
  async uploadImage(@UploadedFile() file: Express.Multer.File) {
    if (!file) {
      throw new BadRequestException('File is required');
    }
    const id = await this.appService.saveImage(file);
    return { id };
  }

  @Get('images/:imageId')
  async shareImage(@Param('imageId') imageId: string, @Res() res: Response) {
    try {
      const { path: filePath, mimetype } = this.appService.getImageDetails(imageId);
      
      // Set content type to ensure browser renders it instead of downloading
      res.setHeader('Content-Type', mimetype);
      
      // Use createReadStream for efficiency with large files
      const stream = fs.createReadStream(filePath);
      stream.pipe(res);
    } catch (error) {
      if (error.status === 404) {
        return res.status(404).json({ error: 'Image not found' });
      }
      return res.status(500).json({ error: 'Internal server error' });
    }
  }
}