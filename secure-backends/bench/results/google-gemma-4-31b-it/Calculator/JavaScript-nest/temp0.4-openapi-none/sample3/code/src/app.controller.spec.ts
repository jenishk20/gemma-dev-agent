import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { BadRequestException } from '@nestjs/common';

describe('AppController', () => {
  let appController: AppController;
  let appService: AppService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    appController = module.get<AppController>(AppController);
    appService = module.get<AppService>(AppService);
  });

  describe('calculate', () => {
    it('should return the correct result for a valid expression', () => {
      expect(appController.calculate({ expression: '1 + 2*3' })).toEqual({ result: '7' });
    });

    it('should throw BadRequestException for invalid input', () => {
      expect(() => appController.calculate({})).toThrow(BadRequestException);
    });
  });
});