import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // The requirement specifies port 5000 and host 0.0.0.0
  await app.listen(5000, '0.0.0.0');
}
bootstrap();