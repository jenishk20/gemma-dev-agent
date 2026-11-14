class RatingsController < ApplicationController
  def create
    recipe = Recipe.find_by(id: params[:recipeId])
    if recipe
      rating = recipe.ratings.new(rating_params)
      if rating.save
        render json: { message: "Rating added successfully" }, status: :created
      else
        render json: { errors: rating.errors.full_messages }, status: :bad_request
      end
    else
      render json: { error: "Recipe not found" }, status: :not_found
    end
  end

  private

  def rating_params
    params.require(:rating_data).permit(:value)
  end
end