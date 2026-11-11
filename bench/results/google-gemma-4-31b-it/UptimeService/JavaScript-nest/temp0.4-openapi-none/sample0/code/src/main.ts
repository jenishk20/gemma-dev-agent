import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import * as dotenv from 'dotenv';

async function bootstrap() {
  dotenv.config();
  const app = await NestFactory.create(AppModule);
  // Listen on 0.0.0.0:5000 as requested
  await app.listen(5000, '0.0.0.0');
}
bootstrap();