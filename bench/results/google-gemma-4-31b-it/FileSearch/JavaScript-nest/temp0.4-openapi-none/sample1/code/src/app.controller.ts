import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('search')
  async search(@Body() body: { search_content?: string | null; search_filename?: string | null; search_dir?: string | null }) {
    // Basic validation to match OpenAPI schema requirements
    if (body === undefined || body === null) {
      throw new BadRequestException('Invalid input');
    }

    try {
      return await this.appService.searchFiles(body);
    } catch (error) {
      throw new BadRequestException(error.message);
    }
  }
}