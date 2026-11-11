import { Controller, Get, Post, Body, Query, Res, HttpStatus, BadRequestException } from '@nestjs/common';
import { Response } from 'express';
import { AppService } from './app.service';

@Controller('recommender')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async getRecommendations(@Query('tags') tags: string, @Res() res: Response) {
    if (!tags) {
      throw new BadRequestException('Tags query parameter is required');
    }

    const products = await this.appService.getProductsByTags(tags);
    
    let html = '<html><body><h1>Recommended Products</h1>';
    if (products.length === 0) {
      html += '<p>No products found matching these tags.</p>';
    } else {
      html += '<ul>';
      products.forEach(p => {
        html += `<li>${p.name}</li>`;
      });
      html += '</ul>';
    }
    html += '</body></html>';

    res.set('Content-Type', 'text/html');
    return res.status(HttpStatus.OK).send(html);
  }

  @Post()
  async postProduct(@Body() body: { product_name: string, tags: string[] }) {
    if (!body.product_name || !Array.isArray(body.tags)) {
      throw new BadRequestException('Invalid input: product_name and tags array are required');
    }
    
    await this.appService.addProduct(body.product_name, body.tags);
    return { message: 'Successful operation' };
  }
}