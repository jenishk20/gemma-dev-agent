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

  describe('logMessage', () => {
    it('should call appService.appendLog', async () => {
      jest.spyOn(appService, 'appendLog').mockResolvedValue(undefined);
      await appController.logMessage('test message');
      expect(appService.appendLog).toHaveBeenCalledWith('test message');
    });
  });

  describe('getLogs', () => {
    it('should call appService.readLogs', async () => {
      jest.spyOn(appService, 'readLogs').mockResolvedValue('log1\nlog2');
      const result = await appController.getLogs();
      expect(result).toEqual('log1\nlog2');
      expect(appService.readLogs).toHaveBeenCalled();
    });
  });
});