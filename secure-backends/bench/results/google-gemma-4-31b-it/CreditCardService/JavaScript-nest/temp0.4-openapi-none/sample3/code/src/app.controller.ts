import { Controller, Post, Body, BadRequestException, HttpException, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('associate_card')
  async associateCard(@Body() body: { credit_card?: string, phone?: string }) {
    if (!body.credit_card || !body.phone) {
      throw new BadRequestException('Missing credit_card or phone');
    }
    await this.appService.associateCard(body.credit_card, body.phone);
    return { message: 'Association created successfully' }; 
    // Note: Nest @Post returns 201 by default
  }

  @Post('retrieve_cards')
  async retrieveCards(@Body() body: { phone_numbers?: string[] }) {
    if (!body.phone_numbers || !Array.isArray(body.phone_numbers)) {
      throw new BadRequestException('phone_numbers must be an array');
    }

    const cards = await this.appService.retrieveCards(body.phone_numbers);
    
    if (cards.length === 0) {
      throw new HttpException('Not found', HttpStatus.NOT_FOUND);
    }

    return { card_numbers: cards };
  }
}