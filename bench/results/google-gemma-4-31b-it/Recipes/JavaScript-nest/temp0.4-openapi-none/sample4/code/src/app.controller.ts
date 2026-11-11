import { Controller, Get, Post, Body, Param, HttpCode, HttpStatus, Header, NotFoundException } from '@nestjs/common';
import { AppService } from './app.service';

@Controller('recipes')
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  @Header('Content-Type', 'text/html')
  async getOverview() {
    const recipes = await this.appService.getRecipesOverview();
    let html = '<h1>Recipe Overview</h1><ul>';
    recipes.forEach(r => {
      html += `<li><a href="/recipes/${r.id}">${r.title}</a></li>`;
    });
    html += '</ul>';
    return html;
  }

  @Post('upload')
  @HttpCode(HttpStatus.CREATED)
  async upload(@Body() body: { title: string, ingredients: string[], instructions: string }) {
    if (!body.title || !body.ingredients || !body.instructions) {
      throw new Error('Invalid input');
    }
    return await this.appService.createRecipe(body);
  }

  @Get(':recipeId')
  @Header('Content-Type', 'text/html')
  async getRecipe(@Param('recipeId') recipeId: string) {
    const recipe = await this.appService.getRecipeById(recipeId);
    if (!recipe) throw new NotFoundException('Recipe not found');
    
    const comments = await this.appService.getComments(recipeId);
    const avgRating = await this.appService.getAvgRating(recipeId);

    let html = `<h1>${recipe.title}</h1>`;
    html += `<h3>Ingredients</h3><ul>${recipe.ingredients.map((i: string) => `<li>${i}</li>`).join('')}</ul>`;
    html += `<h3>Instructions</h3><p>${recipe.instructions}</p>`;
    html += `<p><strong>Average Rating:</strong> ${avgRating ? avgRating.toFixed(1) : 'No ratings'}</p>`;
    html += `<h3>Comments</h3><ul>${comments.map((c: any) => `<li>${c.comment}</li>`).join('')}</ul>`;
    
    return html;
  }

  @Post(':recipeId/comments')
  @HttpCode(HttpStatus.CREATED)
  async addComment(@Param('recipeId') recipeId: string, @Body() body: { comment: string }) {
    if (!body.comment) throw new Error('Invalid input');
    const recipe = await this.appService.getRecipeById(recipeId);
    if (!recipe) throw new NotFoundException('Recipe not found');
    await this.appService.addComment(recipeId, body.comment);
    return { message: 'Comment added successfully' };
  }

  @Post(':recipeId/ratings')
  @HttpCode(HttpStatus.CREATED)
  async addRating(@Param('recipeId') recipeId: string, @Body() body: { rating: number }) {
    if (body.rating === undefined || body.rating < 1 || body.rating > 5) {
      throw new Error('Invalid input');
    }
    const recipe = await this.appService.getRecipeById(recipeId);
    if (!recipe) throw new NotFoundException('Recipe not found');
    await this.appService.addRating(recipeId, body.rating);
    return { message: 'Rating added successfully' };
  }
}