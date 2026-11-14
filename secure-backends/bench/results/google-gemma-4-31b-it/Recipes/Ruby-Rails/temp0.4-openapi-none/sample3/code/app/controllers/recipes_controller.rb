class RecipesController < ApplicationController
  # GET /recipes
  def index
    @recipes = Recipe.all.order(created_at: :desc).limit(10)
    
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
      # The schema asks for text/html for the recipe detail page
      html_content = "<h1>#{@recipe.title}</h1>"
      html_content += "<p><strong>Ingredients:</strong> #{@recipe.ingredients.join(', ')}</p>"
      html_content += "<p><strong>Instructions:</strong> #{@recipe.instructions}</p>"
      html_content += "<p><strong>Average Rating:</strong> #{@recipe.avg_rating || 'No ratings yet'}</p>"
      html_content += "<h3>Comments</h3><ul>"
      @recipe.comments.each { |c| html_content += "<li>#{c.comment}</li>" }
      html_content += "</ul>"
      
      render html: html_content.html_safe
    else
      render json: { error: "Recipe not found" }, status: :not_found
    end
  end

  # POST /recipes/{id}/comments
  def add_comment
    @recipe = Recipe.find_by(id: params[:recipeId])
    return render json: { error: "Recipe not found" }, status: :not_found unless @recipe

    comment = @recipe.comments.build(comment_params)
    if comment.save
      render json: { message: "Comment added successfully" }, status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  # POST /recipes/{id}/ratings
  def add_rating
    @recipe = Recipe.find_by(id: params[:recipeId])
    return render json: { error: "Recipe not found" }, status: :not_found unless @recipe

    rating = @recipe.ratings.build(value: params[:rating])
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

  def comment_params
    params.permit(:comment)
  end

  def recipe_json(recipe)
    {
      id: recipe.id,
      title: recipe.title,
      ingredients: recipe.ingredients,
      instructions: recipe.instructions,
      comments: recipe.comments.map { |c| { comment: c.comment } },
      avgRating: recipe.avg_rating
    }
  end
end