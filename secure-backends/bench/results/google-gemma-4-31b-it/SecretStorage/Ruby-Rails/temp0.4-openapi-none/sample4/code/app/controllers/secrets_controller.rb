class SecretsController < ApplicationController
  before_action :authenticate_request!

  def set_secret
    user = User.find_by(username: params[:username])
    
    if user.nil? || user.id != @current_user_id
      return render json: { message: 'Unauthorized access to this username' }, status: :unauthorized
    end

    secret_record = SecretRecord.find_or_initialize_by(user_id: user.id)
    secret_record.secret_text = params[:secret]
    
    if secret_record.save
      render json: { message: 'Secret has been set successfully' }, status: :ok
    else
      render json: { message: 'Error saving secret' }, status: :internal_server_error
    end
  end

  def get_secret
    user = User.find_by(username: params[:username])
    
    if user.nil? || user.id != @current_user_id
      return render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end

    secret_record = user.secret_record
    if secret_record
      render json: { secret: secret_record.secret_text }, status: :ok
    else
      render json: { secret: nil }, status: :ok
    end
  end
end