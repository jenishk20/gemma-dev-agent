class CommentsController < ApplicationController
  def create
    recipe = Recipe.find_by(id: params[:recipeId])
    if recipe
      comment = recipe.comments.new(comment_params)
      if comment.save
        render json: { message: "Comment added successfully" }, status: :created
      else
        render json: { errors: comment.errors.full_messages }, status: :bad_request
      end
    else
      render json: { error: "Recipe not found" }, status: :not_found
    end
  end

  private

  def comment_params
    params.require(:comment_data).permit(:comment) # Using a wrapper to avoid conflict with params[:comment]
  end
end