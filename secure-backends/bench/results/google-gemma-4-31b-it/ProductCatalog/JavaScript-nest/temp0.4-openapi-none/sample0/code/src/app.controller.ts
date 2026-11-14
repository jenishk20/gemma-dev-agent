import { Controller, Post, Get, Body, Query, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('add')
  async add(@Body() body: any) {
    await this.appService.addProduct(body);
    return { message: 'Product successfully added' };
  }

  @Get('download')
  async download(@Query('name') name: string) {
    return await this.appService.downloadProduct(name);
  }

  @Post('upload')
  @HttpCode(HttpStatus.OK)
  async upload(@Body() body: { name: string, data: string }) {
    if (!body.name || !body.data) {
      throw new Error('Invalid upload query');
    }
    await this.appService.uploadProduct(body.name, body.data);
    return { message: 'The product with the given name was updated.' };
  }

  @Get('search')
  async search(@Query('query') query: string) {
    if (!query) {
      throw new Error('Invalid search query');
    }
    return await this.appService.searchProducts(query);
  }
}