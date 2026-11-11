import { Controller, Get, Post, Body, Query, Res, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('recommender')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async getRecommendations(@Query('tags') tags: string, @Res() res: Response) {
    if (!tags) {
      return res.status(HttpStatus.BAD_REQUEST).send('Missing tags query parameter');
    }

    const products = await this.appService.getProductsByTags(tags);
    
    let html = '<html><body><h1>Recommended Products</h1><ul>';
    if (products.length === 0) {
      html += '<li>No products found matching those tags.</li>';
    } else {
      products.forEach(p => {
        html += `<li>${p.product_name}</li>`;
      });
    }
    html += '</ul></body></html>';

    res.setHeader('Content-Type', 'text/html');
    return res.status(HttpStatus.OK).send(html);
  }

  @Post()
  async postProduct(@Body() body: { product_name: string, tags: string[] }, @Res() res: Response) {
    if (!body.product_name || !Array.isArray(body.tags)) {
      return res.status(HttpStatus.BAD_REQUEST).send('Invalid input');
    }

    try {
      await this.appService.addProduct(body.product_name, body.tags);
      return res.status(HttpStatus.OK).send('Successful operation');
    } catch (e) {
      return res.status(HttpStatus.INTERNAL_SERVER_ERROR).send('Database error');
    }
  }
}