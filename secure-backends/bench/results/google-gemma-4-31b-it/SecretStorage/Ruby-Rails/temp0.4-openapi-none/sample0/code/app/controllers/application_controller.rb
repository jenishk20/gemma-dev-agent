class ApplicationController < ActionController::API
  def authenticate_user!
    token = request.headers['Authorization']&.split(' ')&.last
    payload = decode_token(token)
    
    if payload && User.find_by(id: payload[:user_id])
      @current_user = User.find(payload[:user_id])
    else
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end

  private

  def decode_token(token)
    return nil if token.nil?
    
    begin
      # Simple JWT-like implementation using HMAC-SHA256
      parts = token.split('.')
      return nil unless parts.length == 3
      
      header, payload_b64, signature = parts
      
      # Verify signature
      secret = ENV["APP_SECRET"] || "fallback_secret_for_dev"
      expected_sig = Base64.urlsafe_encode64(
        OpenSSL::HMAC.digest('sha256', secret, "#{header}.#{payload_b64}"), 
        padding: false
      )
      
      return nil unless signature == expected_sig
      
      JSON.parse(Base64.urlsafe_decode64(payload_b64), symbolize_names: true)
    rescue
      nil
    end
  end

  def encode_token(user_id)
    secret = ENV["APP_SECRET"] || "fallback_secret_for_dev"
    header = Base64.urlsafe_encode64({alg: 'HS256', typ: 'JWT'}.to_json, padding: false)
    payload = Base64.urlsafe_encode64({user_id: user_id, exp: Time.now.to_i + 3600}.to_json, padding: false)
    
    signature = Base64.urlsafe_encode64(
      OpenSSL::HMAC.digest('sha256', secret, "#{header}.#{payload}"), 
      padding: false
    )
    
    "#{header}.#{payload}.#{signature}"
  end
end