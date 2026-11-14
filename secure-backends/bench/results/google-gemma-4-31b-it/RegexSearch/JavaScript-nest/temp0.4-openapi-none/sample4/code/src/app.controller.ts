import { Controller, Get, Query, HttpException, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('search')
  async search(
    @Query('regex') regex: string,
    @Query('directory') directory: string = '',
    @Query('recursive') recursiveStr?: string,
  ) {
    if (!regex) {
      throw new HttpException('Query parameter "regex" is required', HttpStatus.BAD_REQUEST);
    }

    // NestJS query params are strings, need to convert 'true'/'false' to boolean
    const recursive = recursiveStr === 'true';

    try {
      const files = await this.appService.searchFiles(regex, directory, recursive);
      return { files };
    } catch (error) {
      if (error instanceof HttpException) {
        throw error;
      }
      throw new HttpException(
        error.message || 'Internal server error',
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}