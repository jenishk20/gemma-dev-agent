class SecretsController < ApplicationController
  before_action :authenticate_user!

  def set_secret
    # The OpenAPI requires the username in the body, but we verify it against the token
    if params[:username] == @current_user.username
      if @current_user.update(secret: params[:secret])
        render json: { message: 'Secret has been set successfully' }, status: :ok
      else
        render json: { message: 'Error saving secret' }, status: :internal_server_error
      end
    else
      render json: { message: 'Username mismatch' }, status: :unauthorized
    end
  end

  def get_secret
    if params[:username] == @current_user.username
      render json: { secret: @current_user.secret }, status: :ok
    else
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end
end