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
  async addToCart(@Body() body: { cart_id: string; item_id: number; count: number }) {
    if (!body.cart_id || body.item_id === undefined || body.count === undefined) {
      throw new Error('Invalid request'); // Will be caught as 400 by Nest if mapped, or we can use ValidationPipe
    }
    return this.appService.addToCart(body.cart_id, body.item_id, body.count);
  }

  @Post('retrieve_cart')
  async retrieveCart(@Body() body: { cart_id: string }) {
    if (!body.cart_id) {
      throw new Error('Invalid request');
    }
    return this.appService.retrieveCart(body.cart_id);
  }
}