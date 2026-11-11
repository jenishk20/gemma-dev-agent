import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('create_cart')
  async createCart() {
    return await this.appService.createCart();
  }

  @Post('add_to_cart')
  @HttpCode(HttpStatus.OK)
  async addToCart(@Body() body: { cart_id: string, item_id: number, count: number }) {
    if (!body.cart_id || body.item_id === undefined || body.count === undefined) {
      throw new Error('Invalid request');
    }
    return await this.appService.addToCart(body.cart_id, body.item_id, body.count);
  }

  @Post('retrieve_cart')
  @HttpCode(HttpStatus.OK)
  async retrieveCart(@Body() body: { cart_id: string }) {
    if (!body.cart_id) {
      throw new Error('Invalid request');
    }
    return await this.appService.retrieveCart(body.cart_id);
  }
}