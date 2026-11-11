import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

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

  describe('retrieveProcesses', () => {
    it('should call appService.getProcesses', async () => {
      const result = {
        filter_flags: 'aux',
        command_regex: 'nest',
      };
      jest.spyOn(appService, 'getProcesses').mockResolvedValue([]);
      await appController.retrieveProcesses(result);
      expect(appService.getProcesses).toHaveBeenCalled();
    });
  });
});