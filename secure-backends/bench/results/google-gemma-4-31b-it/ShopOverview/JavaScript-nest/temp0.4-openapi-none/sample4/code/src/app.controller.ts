import { Controller, Post, Get, Body, Query, Req, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Request, Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('merchants/register')
  async register(@Body() body: any) {
    const { email, name, password } = body;
    if (!email || !name || !password) {
      return { status: 400 }; 
    }
    await this.appService.registerMerchant(email, name, password);
    return { status: 201 };
  }

  @Post('merchants/login')
  async login(@Body() body: any, @Res() res: Response) {
    const { email, password } = body;
    try {
      const token = await this.appService.loginMerchant(email, password);
      res.cookie('AUTH_COOKIE', token, { httpOnly: true });
      return res.status(HttpStatus.OK).send('Login successful');
    } catch (e) {
      return res.status(HttpStatus.UNAUTHORIZED).json({ error: 'Invalid email or password' });
    }
  }

  @Post('merchants/upload-wares')
  async upload(@Body() body: any, @Req() req: Request) {
    const token = req.cookies['AUTH_COOKIE'];
    if (!token) throw new UnauthorizedException();
    
    const { csv } = body;
    if (!csv) throw new BadRequestException('CSV content is required');
    
    await this.appService.uploadWares(token, csv);
    return { message: 'Wares uploaded successfully' };
  }

  @Get('wares')
  async getWares(@Query('minPrice') minPrice: string, @Query('maxPrice') maxPrice: string, @Req() req: Request, @Res() res: Response) {
    const token = req.cookies['AUTH_COOKIE'];
    if (!token) {
      return res.status(HttpStatus.UNAUTHORIZED).send('Unauthorized');
    }
    
    this.appService.verifyToken(token);

    const wares = await this.appService.getWares(
      minPrice ? parseFloat(minPrice) : undefined,
      maxPrice ? parseFloat(maxPrice) : undefined
    );

    let html = '<table><thead><tr><th>Name</th><th>Price</th><th>Description</th><th>Merchant</th></tr></thead><tbody>';
    wares.forEach(w => {
      html += `<tr><td>${w.name}</td><td>${w.price}</td><td>${w.description}</td><td>${w.email}</td></tr>`;
    });
    html += '</tbody></table>';

    return res.setHeader('Content-Type', 'text/html').send(html);
  }
}

// Helper classes to avoid importing from @nestjs/common in the logic if not needed
class UnauthorizedException extends Error {
  constructor() { super('Unauthorized'); this.name = 'UnauthorizedException'; }
}
class BadRequestException extends Error {
  constructor(msg: string) { super(msg); this.name = 'BadRequestException'; }
}