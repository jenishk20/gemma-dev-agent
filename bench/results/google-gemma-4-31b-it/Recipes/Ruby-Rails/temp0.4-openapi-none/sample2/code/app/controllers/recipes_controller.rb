class RecipesController < ApplicationController
  # GET /recipes
  def index
    @recipes = Recipe.order(created_at: :desc).limit(10)
    
    # The schema asks for text/html for the overview
    html_content = "<h1>Recipe Overview</h1><ul>"
    @recipes.each do |r|
      html_content += "<li><a href='/recipes/#{r.id}'>#{r.title}</a></li>"
    end
    html_content += "</ul>"
    
    render html: html_content.html_safe
  end

  # POST /recipes/upload
  def upload
    recipe = Recipe.new(recipe_params)
    if recipe.save
      render json: recipe_json(recipe), status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  # GET /recipes/{id}
  def show
    @recipe = Recipe.find_by(id: params[:id])
    if @recipe
      # The schema asks for text/html for the detail page
      html_content = "<h1>#{@recipe.title}</h1>"
      html_content += "<p><strong>Ingredients:</strong> #{@recipe.ingredients.join(', ')}</p>"
      html_content += "<p><strong>Instructions:</strong> #{@recipe.instructions}</p>"
      html_content += "<p><strong>Average Rating:</strong> #{@recipe.average_rating}</p>"
      html_content += "<h3>Comments</h3><ul>"
      @recipe.comments.each { |c| html_content += "<li>#{c.comment}</li>" }
      html_content += "</ul>"
      
      render html: html_content.html_safe
    else
      render json: { error: "Recipe not found" }, status: :not_found
    end
  end

  private

  def recipe_params
    params.require(:recipe).permit(:title, :ingredients, :instructions)
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