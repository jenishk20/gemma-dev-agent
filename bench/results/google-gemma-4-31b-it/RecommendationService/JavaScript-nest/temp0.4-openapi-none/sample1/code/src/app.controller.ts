import { Controller, Get, Post, Body, Query, Res, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('recommender')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  async getRecommendations(@Query('tags') tags: string, @Res() res: Response) {
    if (!tags) {
      throw new BadRequestException('Tags query parameter is required');
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
    return res.send(html);
  }

  @Post()
  async createProduct(@Body() body: { product_name: string, tags: string[] }) {
    if (!body.product_name || !Array.isArray(body.tags)) {
      throw new BadRequestException('Invalid input: product_name and tags array are required');
    }
    await this.appService.addProduct(body.product_name, body.tags);
    return { message: 'Successful operation' };
  }
}