import { Controller, Get, Post, Body, Param, HttpCode, HttpStatus, Header, HttpException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller('recipes')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  @Header('Content-Type', 'text/html')
  async getOverview() {
    const recipes = await this.appService.getAllRecipesSummary();
    let html = '<h1>Recipe Overview</h1><ul>';
    recipes.forEach(r => {
      html += `<li><a href="/recipes/${r.id}">${r.title}</a></li>`;
    });
    html += '</ul>';
    return html;
  }

  @Post('upload')
  @HttpCode(HttpStatus.CREATED)
  async uploadRecipe(@Body() body: { title: string; ingredients: string[]; instructions: string }) {
    if (!body.title || !body.ingredients || !body.instructions) {
      throw new HttpException('Missing required fields', HttpStatus.BAD_REQUEST);
    }
    return await this.appService.createRecipe(body);
  }

  @Get(':recipeId')
  @Header('Content-Type', 'text/html')
  async getRecipe(@Param('recipeId') recipeId: string) {
    const recipe = await this.appService.getRecipeById(recipeId);
    let html = `<h1>${recipe.title}</h1>`;
    html += `<h3>Ingredients</h3><ul>`;
    recipe.ingredients.forEach((ing: string) => { html += `<li>${ing}</li>`; });
    html += `</ul><h3>Instructions</h3><p>${recipe.instructions}</p>`;
    html += `<p><strong>Average Rating:</strong> ${recipe.avgRating || 'No ratings yet'}</p>`;
    html += `<h3>Comments</h3><ul>`;
    recipe.comments.forEach((c: any) => { html += `<li>${c.comment}</li>`; });
    html += `</ul>`;
    return html;
  }

  @Post(':recipeId/comments')
  @HttpCode(HttpStatus.CREATED)
  async addComment(@Param('recipeId') recipeId: string, @Body() body: { comment: string }) {
    if (!body.comment) {
      throw new HttpException('Comment text is required', HttpStatus.BAD_REQUEST);
    }
    await this.appService.addComment(recipeId, body.comment);
  }

  @Post(':recipeId/ratings')
  @HttpCode(HttpStatus.CREATED)
  async addRating(@Param('recipeId') recipeId: string, @Body() body: { rating: number }) {
    if (body.rating === undefined || body.rating < 1 || body.rating > 5) {
      throw new HttpException('Rating must be between 1 and 5', HttpStatus.BAD_REQUEST);
    }
    await this.appService.addRating(recipeId, body.rating);
  }
}