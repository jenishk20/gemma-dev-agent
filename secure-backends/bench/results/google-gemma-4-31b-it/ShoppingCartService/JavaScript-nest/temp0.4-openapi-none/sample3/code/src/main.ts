import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  
  // Use a global pipe to handle basic validation if needed, 
  // though we handle basic checks in controller for this specific schema
  app.useGlobalPipes(new ValidationPipe());
  
  await app.listen(5000, '0.0.0.0');
}
bootstrap();