import { Controller, Post, Body, BadRequestException, HttpCode, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('associate_card')
  @HttpCode(HttpStatus.CREATED)
  async associateCard(@Body() body: { credit_card?: string, phone?: string }) {
    if (!body.credit_card || !body.phone) {
      throw new BadRequestException('Missing credit_card or phone');
    }
    await this.appService.associateCard(body.credit_card, body.phone);
    return;
  }

  @Post('retrieve_cards')
  @HttpCode(HttpStatus.OK)
  async retrieveCards(@Body() body: { phone_numbers?: string[] }) {
    if (!body.phone_numbers || !Array.isArray(body.phone_numbers)) {
      throw new BadRequestException('phone_numbers must be an array');
    }
    
    const cards = await this.appService.retrieveCards(body.phone_numbers);
    
    if (cards.length === 0) {
      // The schema mentions 404 Not Found for retrieve_cards if not found
      throw new BadRequestException('No cards found associated with all provided phone numbers');
    }

    return { card_numbers: cards };
  }
}