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

  describe('log', () => {
    it('should call appService.logMessage', async () => {
      const spy = jest.spyOn(appService, 'logMessage').mockImplementation(async () => {});
      await appController.log('test message');
      expect(spy).toHaveBeenCalledWith('test message');
    });
  });

  describe('getLogs', () => {
    it('should call appService.getLogs', async () => {
      const spy = jest.spyOn(appService, 'getLogs').mockResolvedValue('log1\nlog2');
      const result = await appController.getLogs();
      expect(spy).toHaveBeenCalled();
      expect(result).toBe('log1\nlog2');
    });
  });
});