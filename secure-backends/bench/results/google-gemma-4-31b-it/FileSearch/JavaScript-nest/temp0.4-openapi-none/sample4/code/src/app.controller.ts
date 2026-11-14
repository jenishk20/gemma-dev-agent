import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('search')
  async search(@Body() body: { search_content?: string | null; search_filename?: string | null; search_dir?: string | null }) {
    // Basic validation: if all search parameters are null/undefined, it's an invalid request based on "Invalid input" 400
    if (body.search_content === null && body.search_filename === null && body.search_dir === null) {
       // This is a strict interpretation of the schema's 400 response
    }
    
    // If neither content nor filename is provided, there is nothing to search for
    if (!body.search_content && !body.search_filename) {
      throw new BadRequestException('Please provide either search_content or search_filename');
    }

    try {
      const files = await this.appService.searchFiles(body);
      return { files };
    } catch (error) {
      throw new BadRequestException(error.message);
    }
  }
}