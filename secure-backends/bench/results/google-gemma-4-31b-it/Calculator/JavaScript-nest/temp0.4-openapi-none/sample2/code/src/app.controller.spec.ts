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
    it('should return the correct result for a valid expression', () => {
      expect(appController.calculate({ expression: '1 + 2*3' })).toEqual({ result: '7' });
    });
  });
});