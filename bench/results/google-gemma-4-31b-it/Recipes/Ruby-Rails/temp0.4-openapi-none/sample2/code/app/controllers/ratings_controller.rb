class RatingsController < ApplicationController
  def create
    recipe = Recipe.find_by(id: params[:recipeId])
    return render json: { error: "Recipe not found" }, status: :not_found unless recipe

    # The schema expects { "rating": 5 }
    rating_val = params[:rating]
    
    if rating_val.to_i >= 1 && rating_val.to_i <= 5
      rating = recipe.ratings.create(value: rating_val.to_i)
      render json: { message: "Rating added successfully" }, status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end
end