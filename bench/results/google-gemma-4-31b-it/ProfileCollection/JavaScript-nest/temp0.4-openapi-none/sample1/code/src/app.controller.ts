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
import { AppService } from './app.service';
import { FileInterceptor } from '@nestjs/platform-express';
import { Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('add_profile')
  @UseInterceptors(FileInterceptor('profile_photo'))
  async addProfile(
    @Body('username') username: string,
    @Body('profile_page') profilePage: string,
    @UploadedFile() file: Express.Multer.File,
    @Res() res: Response
  ) {
    if (!username || !profilePage || !file) {
      return res.status(HttpStatus.BAD_REQUEST).send('Invalid input: username, profile_page, and profile_photo are required');
    }
    
    await this.appService.createProfile(username, profilePage, file.buffer);
    return res.status(HttpStatus.CREATED).send();
  }

  @Get('profile/:username')
  async getProfile(@Param('username') username: string, @Res() res: Response) {
    const html = await this.appService.getProfilePage(username);
    res.setHeader('Content-Type', 'text/html');
    return res.status(HttpStatus.OK).send(html);
  }

  @Get('profile-photo/:username')
  async getPhoto(@Param('username') username: string, @Res() res: Response) {
    const buffer = await this.appService.getProfilePhoto(username);
    res.setHeader('Content-Type', 'image/png');
    return res.status(HttpStatus.OK).send(buffer);
  }
}