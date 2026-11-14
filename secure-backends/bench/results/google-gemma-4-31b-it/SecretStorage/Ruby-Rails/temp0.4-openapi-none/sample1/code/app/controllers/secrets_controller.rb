class SecretsController < ApplicationController
  before_action :authenticate_user!

  def set_secret
    # The OpenAPI spec requires username in the body
    username = params[:username]
    
    if @current_user.username == username
      @current_user.update!(secret_text: params[:secret])
      render json: { message: 'Secret has been set successfully' }, status: :ok
    else
      render json: { message: 'Unauthorized: Username mismatch' }, status: :unauthorized
    end
  end

  def get_secret
    username = params[:username]

    if @current_user.username == username
      render json: { secret: @current_user.secret_text }, status: :ok
    else
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end
end