class RecipesController < ApplicationController
  def index
    @recipes = Recipe.order(created_at: :desc).limit(10)
    
    # The schema asks for text/html for the overview
    html_content = "<h1>Recipe Overview</h1><ul>"
    @recipes.each do |r|
      html_content += "<li>#{r.title} - <a href='/recipes/#{r.id}'>View Recipe</a></li>"
    end
    html_content += "</ul>"
    
    render html: html_content.html_safe
  end

  def upload
    recipe = Recipe.new(recipe_params)
    if recipe.save
      render json: recipe_with_details(recipe), status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  def show
    @recipe = Recipe.find_by(id: params[:recipeId])
    if @recipe
      # The schema asks for text/html for the detailed view
      html_content = "<h1>#{@recipe.title}</h1>"
      html_content += "<p><strong>Ingredients:</strong> #{@recipe.ingredients.join(', ')}</p>"
      html_content += "<p><strong>Instructions:</strong> #{@recipe.instructions}</p>"
      html_content += "<p><strong>Average Rating:</strong> #{@recipe.average_rating || 'No ratings yet'}</p>"
      html_content += "<h3>Comments</h3><ul>"
      @recipe.comments.each { |c| html_content += "<li>#{c.content}</li>" }
      html_content += "</ul>"
      
      render html: html_content.html_safe
    else
      render json: { error: "Recipe not found" }, status: :not_found
    end
  end

  def add_comment
    @recipe = Recipe.find_by(id: params[:recipeId])
    return render json: { error: "Recipe not found" }, status: :not_found unless @recipe

    comment = @recipe.comments.new(content: params[:comment])
    if comment.save
      render json: { message: "Comment added successfully" }, status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  def add_rating
    @recipe = Recipe.find_by(id: params[:recipeId])
    return render json: { error: "Recipe not found" }, status: :not_found unless @recipe

    rating = @recipe.ratings.new(value: params[:rating])
    if rating.save
      render json: { message: "Rating added successfully" }, status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  private

  def recipe_params
    params.permit(:title, :ingredients, :instructions)
  end

  def recipe_with_details(recipe)
    {
      id: recipe.id,
      title: recipe.title,
      ingredients: recipe.ingredients,
      instructions: recipe.instructions,
      comments: recipe.comments.map { |c| { comment: c.content } },
      avgRating: recipe.average_rating
    }
  end
end