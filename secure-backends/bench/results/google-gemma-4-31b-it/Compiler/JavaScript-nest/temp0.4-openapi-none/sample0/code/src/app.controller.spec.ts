import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;
  let appService: AppService;

  beforeEach(async () => {
    const app = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    appController = app.get<AppController>(AppController);
    appService = app.get<AppService>(AppService);
  });

  describe('compile', () => {
    it('should call appService.compileCode', async () => {
      const request = { fileName: 'test.ts', fileContent: 'let x = 1;' };
      const expectedResponse = { hasError: false, compilerError: null };
      
      jest.spyOn(appService, 'compileCode').mockResolvedValue(expectedResponse);
      
      expect(await appController.compile(request)).toBe(expectedResponse);
    });
  });
});