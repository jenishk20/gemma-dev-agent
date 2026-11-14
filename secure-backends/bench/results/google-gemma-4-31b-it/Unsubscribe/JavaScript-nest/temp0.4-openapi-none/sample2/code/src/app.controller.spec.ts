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

  describe('decideUnsubscribe', () => {
    it('should return unsubscribe true for unsubscribe keywords', () => {
      const email = 'From: Alex <alex@example.com>\n\nPlease unsubscribe me.';
      expect(appService.decideUnsubscribe(email)).toEqual({
        email: 'alex@example.com',
        unsubscribe: true,
      });
    });

    it('should return unsubscribe false for neutral emails', () => {
      const email = 'From: Chris <c@sigparser.com>\n\nOk. Just a thought.';
      expect(appService.decideUnsubscribe(email)).toEqual({
        email: 'c@sigparser.com',
        unsubscribe: false,
      });
    });
  });
});