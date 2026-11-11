import { 
  Controller, 
  Post, 
  Get, 
  Param, 
  Body, 
  UseInterceptors, 
  UploadedFile, 
  Res, 
  HttpStatus 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('add_profile')
  @UseInterceptors(FileInterceptor('profile_photo'))
  async addProfile(
    @Body() body: any, 
    @UploadedFile() file: Express.Multer.File,
    @Res() res: Response
  ) {
    const { username, profile_page } = body;
    
    if (!username || !profile_page || !file) {
      return res.status(HttpStatus.BAD_REQUEST).send('Invalid input');
    }

    try {
      await this.appService.addProfile(username, profile_page, file.buffer);
      return res.status(HttpStatus.CREATED).send();
    } catch (error) {
      if (error.status === HttpStatus.FORBIDDEN) {
        return res.status(HttpStatus.FORBIDDEN).send(error.message);
      }
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).send(error.message);
    }
  }

  @Get('profile/:username')
  async getProfile(@Param('username') username: string, @Res() res: Response) {
    try {
      const html = await this.appService.getProfilePage(username);
      res.setHeader('Content-Type', 'text/html');
      return res.send(html);
    } catch (error) {
      return res.status(HttpStatus.NOT_FOUND).send('Profile not found');
    }
  }

  @Get('profile-photo/:username')
  async getPhoto(@Param('username') username: string, @Res() res: Response) {
    try {
      const photo = await this.appService.getProfilePhoto(username);
      res.setHeader('Content-Type', 'image/png');
      return res.send(photo);
    } catch (error) {
      return res.status(HttpStatus.NOT_FOUND).send('Profile photo not found');
    }
  }
}