import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;

  beforeEach(async () => {
    const appTestingModule: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    appController = appTestingModule.get<AppController>(AppController);
  });

  describe('search', () => {
    it('should be defined', () => {
      expect(appController).toBeDefined();
    });
  });
});