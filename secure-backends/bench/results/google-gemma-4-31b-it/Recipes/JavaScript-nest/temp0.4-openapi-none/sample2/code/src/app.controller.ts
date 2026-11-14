import { Controller, Get, Post, Body, Param, HttpCode, Header, Res } from '@nestjs/common';
import { AppService } from './app.service';
import { Response } from 'express';

@Controller('recipes')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  @Header('Content-Type', 'text/html')
  async getOverview(@Res() res: Response) {
    const html = await this.appService.getRecipesOverview();
    res.send(html);
  }

  @Post('upload')
  @HttpCode(201)
  async upload(@Body() body: { title: string, ingredients: string[], instructions: string }) {
    return this.appService.uploadRecipe(body);
  }

  @Get(':recipeId')
  @Header('Content-Type', 'text/html')
  async getRecipe(@Param('recipeId') recipeId: string, @Res() res: Response) {
    try {
      const html = await this.appService.getRecipeById(recipeId);
      res.send(html);
    } catch (e) {
      res.status(404).send('Recipe not found');
    }
  }

  @Post(':recipeId/comments')
  @HttpCode(201)
  async addComment(@Param('recipeId') recipeId: string, @Body('comment') comment: string) {
    return this.appService.addComment(recipeId, comment);
  }

  @Post(':recipeId/ratings')
  @HttpCode(201)
  async addRating(@Param('recipeId') recipeId: string, @Body('rating') rating: number) {
    return this.appService.addRating(recipeId, rating);
  }
}