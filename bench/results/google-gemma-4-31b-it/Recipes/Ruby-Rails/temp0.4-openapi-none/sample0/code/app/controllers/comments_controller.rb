class CommentsController < ApplicationController
  def create
    recipe = Recipe.find_by(id: params[:recipeId])
    return render json: { error: "Recipe not found" }, status: :not_found unless recipe

    comment = recipe.comments.build(comment_params)
    if comment.save
      render json: { message: "Comment added successfully" }, status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  private

  def comment_params
    params.require(:comment_data).permit(:comment)
  end
end