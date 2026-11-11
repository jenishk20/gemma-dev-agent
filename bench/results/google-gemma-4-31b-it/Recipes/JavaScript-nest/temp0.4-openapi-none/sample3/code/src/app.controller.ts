import { Controller, Get, Post, Body, Param, HttpCode, HttpStatus, Header } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('/recipes')
  @Header('Content-Type', 'text/html')
  async getOverview() {
    return this.appService.getRecipesOverview();
  }

  @Post('/recipes/upload')
  async uploadRecipe(@Body() body: { title: string, ingredients: string[], instructions: string }) {
    return this.appService.createRecipe(body);
  }

  @Get('/recipes/:recipeId')
  @Header('Content-Type', 'text/html')
  async getRecipe(@Param('recipeId') recipeId: string) {
    return this.appService.getRecipeById(recipeId);
  }

  @Post('/recipes/:recipeId/comments')
  @HttpCode(HttpStatus.CREATED)
  async addComment(@Param('recipeId') recipeId: string, @Body() body: { comment: string }) {
    await this.appService.addComment(recipeId, body.comment);
    return { message: 'Comment added successfully' };
  }

  @Post('/recipes/:recipeId/ratings')
  @HttpCode(HttpStatus.CREATED)
  async addRating(@Param('recipeId') recipeId: string, @Body() body: { rating: number }) {
    if (body.rating < 1 || body.rating > 5) {
      throw new Error('Rating must be between 1 and 5');
    }
    await this.appService.addRating(recipeId, body.rating);
    return { message: 'Rating added successfully' };
  }
}