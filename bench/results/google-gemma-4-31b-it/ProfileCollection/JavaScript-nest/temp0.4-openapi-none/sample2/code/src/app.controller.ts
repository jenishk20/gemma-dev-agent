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
    @Body('username') username: string,
    @Body('profile_page') profilePage: string,
    @UploadedFile() profilePhoto: Express.Multer.File,
    @Res() res: Response
  ) {
    await this.appService.addProfile(username, profilePage, profilePhoto?.buffer);
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