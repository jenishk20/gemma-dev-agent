import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('create_cart')
  @HttpCode(HttpStatus.CREATED)
  async createCart() {
    return this.appService.createCart();
  }

  @Post('add_to_cart')
  @HttpCode(HttpStatus.OK)
  async addToCart(@Body() body: { cart_id: string; item_id: number; count: number }) {
    const { cart_id, item_id, count } = body;
    if (cart_id === undefined || item_id === undefined || count === undefined) {
      throw new Error('Invalid request');
    }
    return this.appService.addToCart(cart_id, item_id, count);
  }

  @Post('retrieve_cart')
  @HttpCode(HttpStatus.OK)
  async retrieveCart(@Body() body: { cart_id: string }) {
    const { cart_id } = body;
    if (!cart_id) {
      throw new Error('Invalid request');
    }
    return this.appService.retrieveCart(cart_id);
  }
}