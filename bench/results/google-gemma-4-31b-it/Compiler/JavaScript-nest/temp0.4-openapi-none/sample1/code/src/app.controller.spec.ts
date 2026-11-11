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

  describe('compile', () => {
    it('should call appService.compileCode', async () => {
      const dto = { fileName: 'test.ts', fileContent: 'let x = 1;' };
      jest.spyOn(appService, 'compileCode').mockResolvedValue({ hasError: false, compilerError: null });
      
      expect(await appController.compile(dto)).toEqual({ hasError: false, compilerError: null });
      expect(appService.compileCode).toHaveBeenCalledWith(dto.fileName, dto.fileContent);
    });
  });
});