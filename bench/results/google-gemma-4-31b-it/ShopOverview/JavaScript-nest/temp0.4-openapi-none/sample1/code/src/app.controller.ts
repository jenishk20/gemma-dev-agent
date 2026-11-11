import { Controller, Post, Get, Body, Query, Req, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Request, Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('merchants/register')
  async register(@Body() body: any, @Res() res: Response) {
    const { email, name, password } = body;
    await this.appService.registerMerchant(email, name, password);
    return res.status(HttpStatus.CREATED).send();
  }

  @Post('merchants/login')
  async login(@Body() body: any, @Req() req: Request, @Res() res: Response) {
    const { email, password } = body;
    const token = await this.appService.loginMerchant(email, password);
    res.cookie('AUTH_COOKIE', token, { httpOnly: true });
    return res.status(HttpStatus.OK).send('Login successful');
  }

  @Post('merchants/upload-wares')
  async upload(@Body() body: any, @Req() req: Request, @Res() res: Response) {
    const token = req.cookies['AUTH_COOKIE'];
    if (!token) return res.status(HttpStatus.UNAUTHORIZED).send();
    
    await this.appService.uploadWares(token, body.csv);
    return res.status(HttpStatus.OK).send();
  }

  @Get('wares')
  async getWares(
    @Query('minPrice') minPrice: string, 
    @Query('maxPrice') maxPrice: string, 
    @Req() req: Request, 
    @Res() res: Response
  ) {
    const token = req.cookies['AUTH_COOKIE'];
    if (!token) return res.status(HttpStatus.UNAUTHORIZED).send();
    
    this.appService.verifyToken(token); // Validate token
    const html = await this.appService.getWaresHtml(
      minPrice ? parseFloat(minPrice) : undefined, 
      maxPrice ? parseFloat(maxPrice) : undefined
    );
    res.setHeader('Content-Type', 'text/html');
    return res.status(HttpStatus.OK).send(html);
  }
}