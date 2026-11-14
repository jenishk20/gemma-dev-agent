class CommentsController < ApplicationController
  def create
    recipe = Recipe.find_by(id: params[:recipeId])
    return render json: { error: "Recipe not found" }, status: :not_found unless recipe

    comment = recipe.comments.new(comment_params)
    if comment.save
      render json: { message: "Comment added successfully" }, status: :created
    else
      render json: { error: "Invalid input" }, status: :bad_request
    end
  end

  private

  def comment_params
    params.require(:comment_data).permit(:comment) 
    # Note: Since the schema shows a flat JSON body { "comment": "..." }, 
    # we handle the params mapping in the route or here.
    # To match the schema exactly:
    params.permit(:comment)
  end
end