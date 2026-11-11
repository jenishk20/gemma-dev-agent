import { 
  Controller, 
  Post, 
  Get, 
  Param, 
  Body, 
  UseInterceptors, 
  UploadedFile, 
  Res, 
  BadRequestException 
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
    @UploadedFile() file: Express.Multer.File,
    @Res() res: Response
  ) {
    if (!username || !profilePage || !file) {
      throw new BadRequestException('Missing required fields: username, profile_page, or profile_photo');
    }

    if (file.mimetype !== 'image/png') {
      throw new BadRequestException('Only PNG images are allowed');
    }

    await this.appService.addProfile(username, profilePage, file.buffer);
    return res.status(201).send();
  }

  @Get('profile/:username')
  async getProfile(@Param('username') username: string, @Res() res: Response) {
    const html = await this.appService.getProfilePage(username);
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }

  @Get('profile-photo/:username')
  async getPhoto(@Param('username') username: string, @Res() res: Response) {
    const buffer = await this.appService.getProfilePhoto(username);
    res.setHeader('Content-Type', 'image/png');
    return res.send(buffer);
  }
}