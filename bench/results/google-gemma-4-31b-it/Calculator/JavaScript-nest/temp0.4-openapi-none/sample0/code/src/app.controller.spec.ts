import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;
  let appService: AppService;

  beforeEach(async () => {
    const appModule: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    appController = appModule.get<AppController>(AppController);
    appService = appModule.get<AppService>(AppService);
  });

  describe('calculate', () => {
    it('should return the correct result for a valid expression', () => {
      const result = appController.calculate({ expression: '1 + 2*3' });
      expect(result.result).toBe('7');
    });

    it('should return the correct result for division', () => {
      const result = appController.calculate({ expression: '10 / 2' });
      expect(result.result).toBe('5');
    });
  });
});