require 'jwt'

class SecretsController < ApplicationController
  before_action :authenticate_user!

  def set_secret
    # The schema requires username in body, but we verify identity via JWT
    user = User.find_by(username: params[:username])
    
    if user && user.id == current_user.id
      secret_store = SecretStore.find_or_initialize_by(user: user)
      secret_store.secret = params[:secret]
      if secret_store.save
        render json: { message: 'Secret has been set successfully' }, status: :ok
      else
        render json: { message: 'Error saving secret' }, status: :internal_server_error
      end
    else
      render json: { message: 'Unauthorized: Username mismatch' }, status: :unauthorized
    end
  end

  def get_secret
    user = User.find_by(username: params[:username])
    
    if user && user.id == current_user.id
      secret_store = SecretStore.find_by(user: user)
      if secret_store
        render json: { secret: secret_store.secret }, status: :ok
      else
        render json: { secret: nil }, status: :ok
      end
    else
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end
end