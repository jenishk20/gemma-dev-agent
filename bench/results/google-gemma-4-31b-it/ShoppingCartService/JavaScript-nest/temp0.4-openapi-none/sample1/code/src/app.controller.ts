import { Controller, Post, Body, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('create_cart')
  async createCart() {
    return this.appService.createCart();
  }

  @Post('add_to_cart')
  @HttpCode(HttpStatus.OK)
  async addToCart(@Body() body: { cart_id: string; item_id: number; count: number }) {
    await this.appService.addToCart(body.cart_id, body.item_id, body.count);
    return {};
  }

  @Post('retrieve_cart')
  @HttpCode(HttpStatus.OK)
  async retrieveCart(@Body() body: { cart_id: string }) {
    return this.appService.retrieveCart(body.cart_id);
  }
}