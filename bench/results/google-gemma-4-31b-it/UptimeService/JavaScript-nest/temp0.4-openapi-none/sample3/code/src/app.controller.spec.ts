import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;
  let appService: AppService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [
        {
          provide: AppService,
          useValue: {
            registerHeartbeat: jest.fn(),
            getServicesByToken: jest.fn().mockResolvedValue([]),
          },
        },
      ],
    }).compile();

    appController = module.get<AppController>(AppController);
    appService = module.get<AppService>(AppService);
  });

  describe('heartbeat', () => {
    it('should register a heartbeat', async () => {
      const dto = { serviceId: 'test', token: 'pass' };
      await appController.heartbeat(dto);
      expect(appService.registerHeartbeat).toHaveBeenCalledWith('test', 'pass');
    });
  });
});