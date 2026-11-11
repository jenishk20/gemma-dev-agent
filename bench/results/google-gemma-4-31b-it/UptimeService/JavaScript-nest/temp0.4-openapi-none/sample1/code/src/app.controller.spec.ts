import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;
  let appService: AppService;

  beforeEach(async () => {
    const appModule: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [
        {
          provide: AppService,
          useValue: {
            registerHeartbeat: jest.fn(),
            getServicesByToken: jest.fn(),
          },
        },
      ],
    }).compile();

    appController = appModule.get<AppController>(AppController);
    appService = appModule.get<AppService>(AppService);
  });

  describe('heartbeat', () => {
    it('should call registerHeartbeat', async () => {
      const dto = { serviceId: 'test', token: 'pass' };
      await appController.heartbeat(dto);
      expect(appService.registerHeartbeat).toHaveBeenCalledWith('test', 'pass');
    });
  });
});