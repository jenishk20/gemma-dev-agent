import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;

  beforeEach(async () => {
    const appModule: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    appController = appModule.get<AppController>(AppController);
  });

  describe('controller', () => {
    it('should be defined', () => {
      expect(appController).toBeDefined();
    });
  });
});