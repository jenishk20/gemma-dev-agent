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

  describe('calculate', () => {
    it('should calculate 1 + 2*3 to be 7', () => {
      expect(appController.calculate({ expression: '1 + 2*3' })).toEqual({ result: '7' });
    });

    it('should handle decimals', () => {
      expect(appController.calculate({ expression: '10 / 4' })).toEqual({ result: '2.5' });
    });
  });
});