import { Controller, Post, Body, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

interface SearchRequest {
  search_content: string | null;
  search_filename: string | null;
  search_dir: string | null;
}

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('/search')
  async search(@Body() body: SearchRequest) {
    // Basic validation to ensure the body is an object
    if (!body || typeof body !== 'object') {
      throw new BadRequestException('Invalid input');
    }

    const { search_content, search_filename, search_dir } = body;

    // If all search parameters are null, we return an empty list or handle as invalid
    if (search_content === null && search_filename === null) {
        // According to the schema, we should return files that match. 
        // If nothing is specified, we return empty.
        return { files: [] };
    }

    try {
      const files = await this.appService.searchFiles(search_content, search_filename, search_dir);
      return { files };
    } catch (error) {
      throw new BadRequestException('Invalid input or directory access error');
    }
  }
}