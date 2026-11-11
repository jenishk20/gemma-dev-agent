import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;

  beforeEach(async () => {
    const appTestingModule: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [
        {
          provide: AppService,
          useValue: {
            registerClick: jest.fn(),
            getClicks: jest.fn(),
          },
        },
      ],
    }).compile();

    appController = appTestingModule.get<AppController>(AppController);
  });

  describe('registerClick', () => {
    it('should be defined', () => {
      expect(appController).toBeDefined();
    });
  });
});