import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { json, urlencoded } from 'express';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  
  // Enable JSON and URL-encoded bodies to support both API and HTML Form submissions
  app.use(json());
  app.use(urlencoded({ extended: true }));

  await app.listen(5000, '0.0.0.0');
}
bootstrap();