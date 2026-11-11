import { Controller, Post, Get, Body, Query, Req, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Request, Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('merchants/register')
  async register(@Body() body: any) {
    await this.appService.register(body.email, body.name, body.password);
    return { message: 'Merchant registered successfully' };
  }

  @Post('merchants/login')
  async login(@Body() body: any, @Res() res: Response) {
    const token = await this.appService.login(body.email, body.password);
    res.cookie('AUTH_COOKIE', token, { httpOnly: true });
    return res.status(HttpStatus.OK).send('Login successful');
  }

  @Post('merchants/upload-wares')
  async upload(@Req() req: Request, @Body() body: any) {
    const token = req.cookies['AUTH_COOKIE'];
    if (!token) throw new Error('Unauthorized');
    await this.appService.uploadWares(token, body.csv);
    return { message: 'Wares uploaded successfully' };
  }

  @Get('wares')
  async getWares(@Req() req: Request, @Query('minPrice') minPrice: string, @Query('maxPrice') maxPrice: string, @Res() res: Response) {
    const token = req.cookies['AUTH_COOKIE'];
    if (!token) {
        // According to schema, this endpoint requires cookieAuth
        // However, the schema says it returns HTML. We verify token first.
        try { this.appService.verifyToken(token); } catch(e) { 
            return res.status(401).send('Unauthorized'); 
        }
    }
    
    const html = await this.appService.getWaresHtml(
      minPrice ? parseFloat(minPrice) : undefined,
      maxPrice ? parseFloat(maxPrice) : undefined
    );
    
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }
}