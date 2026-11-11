class ApplicationController < ActionController::API
  def authenticate_request!
    header = request.headers['Authorization']
    token = header&.split(' ')&.last
    
    if token && valid_token?(token)
      @current_user_id = decode_token(token)
    else
      render json: { message: 'Invalid authentication token' }, status: :unauthorized
    end
  end

  private

  def valid_token?(token)
    begin
      decode_token(token)
      true
    rescue
      false
    end
  end

  def decode_token(token)
    parts = token.split('.')
    return nil unless parts.length == 3
    
    payload_b64, signature = parts[0..1].join('.'), parts[2]
    expected_signature = generate_signature(parts[0..1].join('.'))
    
    if signature == expected_signature
      payload = JSON.parse(Base64.decode64(payload_b64))
      return payload['user_id']
    end
    nil
  end

  def generate_signature(data)
    secret = ENV['APP_SECRET'] || 'default_secret'
    OpenSSL::HMAC.hexdigest('sha256', secret, data)
  end
end