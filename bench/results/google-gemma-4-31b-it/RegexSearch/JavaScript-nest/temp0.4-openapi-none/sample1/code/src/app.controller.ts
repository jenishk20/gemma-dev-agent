import { Controller, Get, Query, BadRequestException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('/search')
  async search(
    @Query('regex') regex: string,
    @Query('directory') directory?: string,
    @Query('recursive') recursive?: string,
  ) {
    if (!regex) {
      throw new BadRequestException('Regex parameter is required');
    }

    // NestJS query params are strings, convert recursive to boolean
    const isRecursive = recursive === 'true';
    
    try {
      const files = await this.appService.searchFiles(regex, directory || '', isRecursive);
      return { files };
    } catch (error) {
      if (error instanceof BadRequestException) {
        throw error;
      }
      throw new BadRequestException(error.message);
    }
  }
}