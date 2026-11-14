import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // Start the webserver on port 5000 and listen on all interfaces
  await app.listen(5000, '0.0.0.0');
}
bootstrap();