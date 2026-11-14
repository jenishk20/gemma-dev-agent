class SecretsController < ApplicationController
  before_action :authenticate_user!

  def set_secret
    # The schema requires username in body, but we validate against the authenticated user
    user = User.find_by(username: params[:username])
    
    if user && user.id == @current_user.id
      secret_rec = SecretRecord.find_or_initialize_by(user_id: user.id)
      secret_rec.update(secret_text: params[:secret])
      render json: { message: 'Secret has been set successfully' }, status: :ok
    else
      render json: { message: 'Unauthorized' }, status: :unauthorized
    end
  end

  def get_secret
    user = User.find_by(username: params[:username])
    
    if user && user.id == @current_user.id
      secret_rec = SecretRecord.find_by(user_id: user.id)
      render json: { secret: secret_rec&.secret_text || "" }, status: :ok
    else
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end
end