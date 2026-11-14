import { Test, TestingModule } from '@nestjs/testing';
import { AppController } from './app.controller';
import { AppService } from './app.service';

describe('AppController', () => {
  let appController: AppController;

  beforeEach(async () => {
    const appTestingModule: TestingModule = await Test.createTestingModule({
      controllers: [AppController],
      providers: [AppService],
    }).compile();

    appController = appTestingModule.get<AppController>(AppController);
  });

  it('should decide unsubscribe for a request containing keywords', () => {
    const rawEmail = 'From: Alex <alex@example.com>\n\nPlease unsubscribe me';
    expect(appController.decideUnsubscribe(rawEmail).unsubscribe).toBe(true);
    expect(appController.decideUnsubscribe(rawEmail).email).toBe('alex@example.com');
  });

  it('should not decide unsubscribe for a neutral email', () => {
    const rawEmail = 'From: Chris <c@sigparser.com>\n\nOk. Just a thought.';
    expect(appController.decideUnsubscribe(rawEmail).unsubscribe).toBe(false);
  });
});