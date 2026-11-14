import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('search')
  async search(@Body() body: { search_content?: string | null; search_filename?: string | null; search_dir?: string | null }) {
    // Basic validation to ensure at least one search parameter is provided
    if (body.search_content === undefined && body.search_filename === undefined && body.search_dir === undefined) {
      throw new BadRequestException('Invalid input: Please provide search criteria');
    }

    return await this.appService.searchFiles(body);
  }
}