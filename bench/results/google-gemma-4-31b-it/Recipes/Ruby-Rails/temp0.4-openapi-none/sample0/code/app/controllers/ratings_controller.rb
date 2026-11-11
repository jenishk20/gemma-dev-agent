class RatingsController < ApplicationController
  def create
    recipe = Recipe.find_by(id: params[:recipeId])
    return render json: { error: "Recipe not found" }, status: :not_found unless recipe

    rating = recipe.ratings.build(value: params[:rating_data][:rating])
    if rating.save
      render json: { message: "Rating added successfully" }, status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end
end