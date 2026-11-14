class RecipesController < ApplicationController
  def index
    @recipes = Recipe.order(created_at: :desc).limit(10)
    
    # The schema asks for text/html for the overview
    render html: "<h1>Recipe Overview</h1><ul>" + 
                @recipes.map { |r| "<li><a href='/recipes/#{r.id}'>#{r.title}</a></li>" }.join + 
                "</ul>".html_safe
  end

  def upload
    recipe = Recipe.new(recipe_params)
    if recipe.save
      render json: recipe_json(recipe), status: :created
    else
      render json: { errors: recipe.errors.full_messages }, status: :bad_request
    end
  end

  def show
    @recipe = Recipe.find_by(id: params[:recipeId])
    if @recipe
      # The schema asks for text/html for the recipe details
      comments_html = @recipe.comments.map { |c| "<li>#{c.comment}</li>" }.join
      render html: "<h1>#{@recipe.title}</h1>" +
                   "<p><strong>Ingredients:</strong> #{@recipe.ingredients.join(', ')}</p>" +
                   "<p><strong>Instructions:</strong> #{@recipe.instructions}</p>" +
                   "<p><strong>Avg Rating:</strong> #{@recipe.average_rating || 'No ratings'}</p>" +
                   "<h3>Comments</h3><ul>#{comments_html}</ul>".html_safe
    else
      render json: { error: "Recipe not found" }, status: :not_found
    end
  end

  private

  def recipe_params
    params.require(:recipe).permit(:title, :instructions, ingredients: [])
  end

  def recipe_json(recipe)
    {
      id: recipe.id,
      title: recipe.title,
      ingredients: recipe.ingredients,
      instructions: recipe.instructions,
      comments: recipe.comments.map { |c| { comment: c.comment } },
      avgRating: recipe.average_rating
    }
  end
end