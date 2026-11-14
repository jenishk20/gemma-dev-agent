import { Controller, Post, Get, Body, Query, Req, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Request, Response } from 'express';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('merchants/register')
  async register(@Body() body: { email: string, name: string, password: string }) {
    await this.appService.registerMerchant(body.email, body.name, body.password);
    return { message: 'Merchant registered successfully' };
  }

  @Post('merchants/login')
  async login(@Body() body: { email: string, password: string }, @Res() res: Response) {
    const token = await this.appService.loginMerchant(body.email, body.password);
    res.cookie('AUTH_COOKIE', token, { httpOnly: true });
    return res.status(HttpStatus.OK).send('Login successful');
  }

  @Post('merchants/upload-wares')
  async upload(@Body() body: { csv: string }, @Req() req: Request) {
    const token = req.cookies['AUTH_COOKIE'];
    if (!token) throw new UnauthorizedException();
    const payload = this.appService.verifyToken(token);
    await this.appService.uploadWares(payload.id, body.csv);
    return { message: 'Wares uploaded successfully' };
  }

  @Get('wares')
  async getWares(
    @Query('minPrice') minPrice: string, 
    @Query('maxPrice') maxPrice: string, 
    @Req() req: Request, 
    @Res() res: Response
  ) {
    const token = req.cookies['AUTH_COOKIE'];
    if (!token) throw new UnauthorizedException();
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
    
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }
}

// Helper to avoid importing from @nestjs/common inside the controller for the exception
function UnauthorizedException() {
  const err = new Error('Unauthorized');
  (err as any).status = 401;
  return err;
}