import { Controller, Post, Body } from '@nestjs/common';
import { AppService } from './app.service';

interface CompileRequest {
  fileName: string;
  fileContent: string;
}

interface CompileResponse {
  hasError: boolean;
  compilerError: string | null;
}

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Post('compile')
  async compile(@Body() body: CompileRequest): Promise<CompileResponse> {
    return this.appService.compileCode(body.fileName, body.fileContent);
  }
}