import { Controller, Get, Post, Body, Query, HttpCode, HttpStatus, Res } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('recommender')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async getRecommendations(@Query('tags') tags: string, @Res() res: Response) {
    const html = await this.appService.getRecommendations(tags);
    res.setHeader('Content-Type', 'text/html');
    return res.send(html);
  }

  @Post()
  @HttpCode(HttpStatus.OK)
  async postProduct(@Body() body: { product_name: string, tags: string[] }) {
    return await this.appService.addProduct(body.product_name, body.tags);
  }
}