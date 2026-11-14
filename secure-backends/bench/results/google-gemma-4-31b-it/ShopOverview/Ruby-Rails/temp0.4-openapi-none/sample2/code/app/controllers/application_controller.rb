class ApplicationController < ActionController::API
  include ActionController::Cookies
  include ActionController::RequestForgeryProtection

  def authenticate_merchant!
    merchant_id = cookies.signed[:AUTH_COOKIE]
    @current_merchant = Merchant.find_by(id: merchant_id)
    
    unless @current_merchant
      render json: { error: 'Unauthorized' }, status: :unauthorized
    end
  end
end