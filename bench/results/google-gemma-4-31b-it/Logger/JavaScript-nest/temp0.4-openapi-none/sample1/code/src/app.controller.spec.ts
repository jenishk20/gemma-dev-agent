import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;
  let appService: AppService;

  beforeEach(async () => {
    const app: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    appController = app.get<AppController>(AppController);
    appService = app.get<AppService>(AppService);
  });

  describe('logMessage', () => {
    it('should call appService.addLog', async () => {
      const spy = jest.spyOn(appService, 'addLog');
      await appController.logMessage({ message: 'test log' });
      expect(spy).toHaveBeenCalledWith('test log');
    });
  });

  describe('retrieveLogs', () => {
    it('should call appService.getLogs', async () => {
      const spy = jest.spyOn(appService, 'getLogs').mockResolvedValue('log1\nlog2');
      const result = await appController.retrieveLogs();
      expect(spy).toHaveBeenCalled();
      expect(result).toBe('log1\nlog2');
    });
  });
});