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

  describe('calculate', () => {
    it('should calculate 1 + 2*3 as 7', () => {
      expect(appController.calculate({ expression: '1 + 2*3' }).result).toBe('7');
    });

    it('should calculate 10 / 2 as 5', () => {
      expect(appController.calculate({ expression: '10 / 2' }).result).toBe('5');
    });
  });
});