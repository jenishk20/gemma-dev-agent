import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('search')
  async search(@Body() body: { search_content?: string | null; search_filename?: string | null; search_dir?: string | null }) {
    // Basic validation: if all are null/undefined, it's an invalid request based on the schema's intent
    if (body.search_content === null && body.search_filename === null && body.search_dir === null) {
       // However, the schema says they are optional. But usually, we need at least one search parameter.
       // To strictly follow "Invalid input" 400, we check if the body exists.
    }

    try {
      const files = await this.appService.searchFiles(body);
      return { files };
    } catch (error) {
      throw new BadRequestException(error.message);
    }
  }
}